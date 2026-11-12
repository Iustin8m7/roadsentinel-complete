import { useDataStore } from "@/store/data";
import { USERS } from "@/mocks/users";
import { ROLE_LABEL } from "@/lib/constants";
import { ROLE_PERMISSIONS } from "@/lib/permissions";
import { BadgePanel } from "@/components/BadgePanel";
import { api, USE_MOCKS } from "@/lib/api";
import { Banner } from "@/components/ui";
import { Shield, Sliders, Users } from "lucide-react";
import { useState } from "react";

export default function SettingsPage() {
  const settings = useDataStore((s) => s.settings);
  const update = useDataStore((s) => s.updateSettings);
  const [error, setError] = useState("");
  const saveSound = async (enabled: boolean) => {
    if (USE_MOCKS) return update({ soundOnCritical: enabled });
    try {
      const saved = await api<{sound_on_critical:boolean}>("/api/notifications/preferences", {method:"PUT", body:JSON.stringify({sound_on_critical:enabled})});
      update({ soundOnCritical: saved.sound_on_critical }); setError("");
    } catch { setError("Preferința de notificare nu a putut fi salvată."); }
  };

  return (
    <div className="h-full grid grid-cols-1 md:grid-cols-2 gap-4 p-6 bg-void">
      {/* Notifications: the only setting with a real effect in the connected app */}
      <BadgePanel
        title="Notificări"
        icon={<Sliders className="w-4 h-4 text-accent" />}
        contentClassName="space-y-4"
      >
        <label className="flex items-center gap-3 cursor-pointer text-xs font-semibold text-text-primary">
          <input
            type="checkbox"
            checked={settings.soundOnCritical}
            onChange={(e) => void saveSound(e.target.checked)}
            className="w-4 h-4 rounded border-border bg-void text-accent focus:ring-0 cursor-pointer"
          />
          <span>Semnal sonor la incidente critice</span>
        </label>
        {error && <p role="alert">{error}</p>}
      </BadgePanel>

      {/* Privacy & GDPR */}
      <BadgePanel
        title="Principii de funcționare"
        icon={<Shield className="w-4 h-4 text-ok" />}
        contentClassName="space-y-3"
      >
        <div className="p-3.5 rounded-md bg-elevation/70 border border-border text-xs text-text-secondary space-y-2">
          <p className="font-semibold text-text-primary">Cum funcționează sistemul:</p>
          <ul className="space-y-1.5 list-disc pl-4 text-xs">
            <li>Sistemul nu efectuează recunoaștere facială.</li>
            <li>Decizia aparține operatorului uman; sistemul nu emite sancțiuni automat.</li>
            <li>Deciziile și accesările sunt înregistrate în jurnalul de audit.</li>
          </ul>
        </div>
      </BadgePanel>

      {/* System Users Table: mock data only */}
      {USE_MOCKS && <div className="md:col-span-2">
        <Banner tone="warn">Demonstrativ: utilizatori fictivi, nu provin din sistem.</Banner>
        <BadgePanel
          title="Utilizatori și Permisiuni Sistem"
          icon={<Users className="w-4 h-4 text-accent" />}
          contentClassName="p-0 overflow-x-auto"
        >
          <table className="w-full text-left text-xs border-collapse">
            <thead className="sticky top-0 bg-elevation border-b border-border font-mono text-text-secondary text-xs">
              <tr>
                <th className="py-2.5 px-4">UTILIZATOR</th>
                <th className="py-2.5 px-4">NUME</th>
                <th className="py-2.5 px-4">ROL</th>
                <th className="py-2.5 px-4">UNITATE</th>
                <th className="py-2.5 px-4 text-right">DREPTURI</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60">
              {USERS.map((u) => (
                <tr key={u.id} className="hover:bg-elevation/50 transition-colors">
                  <td className="py-3 px-4 font-mono font-bold text-accent">
                    {u.username}
                  </td>
                  <td className="py-3 px-4 text-text-primary font-medium">
                    {u.rank} {u.fullName}
                  </td>
                  <td className="py-3 px-4 font-mono text-xs text-text-primary">
                    <span className="px-2 py-0.5 rounded bg-elevation border border-border">
                      {ROLE_LABEL[u.role].toUpperCase()}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-text-secondary">{u.unit}</td>
                  <td className="py-3 px-4 text-right font-mono text-text-secondary">
                    {ROLE_PERMISSIONS[u.role].length} permisiuni
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </BadgePanel>
      </div>}
    </div>
  );
}
