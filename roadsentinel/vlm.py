"""Second opinion from a vision-language model on each flagged clip.

Looks only at frames from the event clip, confirms or rejects the alert and writes
a short Romanian description for the operator. Skipped when no API key is configured.

Usage: python -m roadsentinel.vlm            # verify all pending events
"""
import base64
import os
from typing import Literal

from pydantic import BaseModel

from . import media, store

MODEL = "claude-opus-5-5"

PROMPT = """Ești asistentul unui dispecerat de poliție rutieră. Un sistem automat (detector + reguli) a semnalat un eveniment pe o cameră de trafic.

Eveniment semnalat: {label}
Regula care a declanșat alerta: {rule}
Obiect urmărit: {object_class}, viteză estimată din video: {speed}

Primești {n} cadre din clipul evenimentului, în ordine cronologică. Vehiculul vizat este încadrat cu un dreptunghi colorat în cadrul cheie.

Spune dacă imaginile susțin alerta. Fii conservator: confirmă doar ce se vede. Viteza nu se poate verifica vizual exact; în acest caz judecă doar dacă scena e plauzibilă (vehicul real, pe carosabil, nu o eroare de detecție).
Scrie descrierea în română, o propoziție scurtă și factuală, pentru operator (ex.: „Camion oprit pe banda de urgență, avarii pornite, două persoane lângă el.”)."""


class Verdict(BaseModel):
    verdict: Literal["confirmed", "rejected", "uncertain"]
    confidence: float
    description_ro: str
    reason: str


def available():
    return os.environ.get("RS_EXTERNAL_AI", "off") == "frames" and bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


def _frames(event, n_extra=2):
    import cv2

    imgs = [media.local_path(event["keyframe"]).read_bytes()]
    cap = cv2.VideoCapture(str(media.local_path(event["clip"])))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    for i in range(n_extra):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(total * (i + 1) / (n_extra + 2)))
        ok, f = cap.read()
        if ok:
            imgs.append(cv2.imencode(".jpg", cv2.resize(f, (1280, 720)))[1].tobytes())
    cap.release()
    return imgs


def verify(event, client=None):
    if os.environ.get("RS_EXTERNAL_AI", "off") != "frames":
        return None
    import anthropic

    client = client or anthropic.Anthropic()
    imgs = _frames(event)
    content = [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                            "data": base64.standard_b64encode(b).decode()}} for b in imgs]
    content.append({"type": "text", "text": PROMPT.format(
        label=event["type"], rule=event["rule"], object_class=event["object_class"] or "-",
        speed=f"{event['speed_kmh']} km/h" if event["speed_kmh"] else "-", n=len(imgs))})
    resp = client.messages.parse(model=MODEL, max_tokens=4000,
                                 messages=[{"role": "user", "content": content}], output_format=Verdict)
    if resp.stop_reason == "refusal" or resp.parsed_output is None:
        return None
    return resp.parsed_output


def check(event):
    """Fields to store on a new event: VLM verdict, or 'skipped' when no API key is set."""
    if os.environ.get("RS_EXTERNAL_AI", "off") != "frames":
        return {"vlm_status": "skipped", "vlm_text": "Verificare VLM dezactivată prin RS_EXTERNAL_AI."}
    if not available():
        return {"vlm_status": "skipped", "vlm_text": "Verificare VLM indisponibilă (lipsește ANTHROPIC_API_KEY)."}
    import anthropic

    try:
        v = verify(event)
    except anthropic.APIError as err:
        print(f"VLM error: {err}")
        return {"vlm_status": "pending"}
    if v is None:
        return {"vlm_status": "pending"}
    status = {"confirmed": "confirmed", "rejected": "rejected"}.get(v.verdict, "uncertain")
    return {"vlm_status": status, "vlm_text": v.description_ro, "vlm": v.model_dump()}


def verify_pending(db):
    pending = store.query_events(db, vlm_status="pending")
    if not available():
        for e in pending:
            store.set_vlm(db, e["id"], "skipped", "Verificare VLM indisponibilă (lipsește ANTHROPIC_API_KEY).")
        return 0
    import anthropic

    client = anthropic.Anthropic()
    done = 0
    for e in pending:
        try:
            v = verify(e, client)
        except anthropic.APIError as err:
            print(f"VLM error on event {e['id']}: {err}")
            continue
        if v is None:
            continue
        status = {"confirmed": "confirmed", "rejected": "rejected"}.get(v.verdict, "uncertain")
        store.set_vlm(db, e["id"], status, v.description_ro, verdict=v.model_dump(), actor=f"vlm:{MODEL}")
        done += 1
    return done


if __name__ == "__main__":
    print("Verificate:", verify_pending(store.connect()))
