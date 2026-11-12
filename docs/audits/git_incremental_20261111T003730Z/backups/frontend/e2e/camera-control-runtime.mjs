import fs from 'node:fs'
import { execFileSync } from 'node:child_process'
import { chromium, expect } from '@playwright/test'
const browser = await chromium.launch({ headless:true })
try {
  const session=process.env.RS_CAMERA_SESSION
  const context=await browser.newContext({viewport:{width:1440,height:1000},...(session && fs.existsSync(session)?{storageState:session}:{})})
  const page = await context.newPage()
  const origin=process.env.RS_UI_ORIGIN
  await page.goto(origin+'/app/camere')
  if(!session || !fs.existsSync(session)) {
    await page.getByLabel('Utilizator').fill(process.env.RS_UI_USER)
    await page.getByLabel('Parolă',{exact:true}).fill(process.env.RS_UI_PASSWORD)
    await page.getByRole('button',{name:'Intră',exact:true}).click()
    const otp=process.env.RS_UI_TOTP_SECRET ? execFileSync(process.env.RS_UI_PYTHON,['-c','import pyotp,sys;print(pyotp.TOTP(sys.stdin.read()).now())'],{input:process.env.RS_UI_TOTP_SECRET,encoding:'utf8'}).trim() : process.env.RS_UI_TOTP
    await page.locator('input[name="code"]').fill(otp)
    await page.getByRole('button',{name:'Verifică',exact:true}).click()
  }
  await page.waitForURL(origin+'/app/camere')
  const authenticated=await context.request.get(origin+'/api/auth/me');expect(authenticated.status()).toBe(200)
  if(session) {await context.storageState({path:session});fs.chmodSync(session,0o600)}
  if(process.env.RS_CAMERA_TASK==='register') {
    await page.getByRole('button',{name:'Adaugă cameră',exact:true}).click()
    await page.screenshot({path:process.env.RS_E2E_SCREENSHOT.replace('.png','-form.png')})
    await page.getByLabel('Nume cameră',{exact:true}).fill('LOCAL RECORDED REPLAY')
    await page.getByLabel('ID cameră (slug)',{exact:true}).fill('mission-replay')
    await page.getByLabel('Locație / drum',{exact:true}).fill('Licensed local replay; synthetic scene geometry')
    const created=page.waitForResponse(r=>r.request().method()==='POST' && new URL(r.url()).pathname==='/api/cameras')
    await page.getByRole('button',{name:'Adaugă camera',exact:true}).click()
    const result=await created
    expect(result.status()).toBe(201)
    fs.writeFileSync(process.env.RS_CAMERA_RESULT,JSON.stringify(await result.json()),{mode:0o600})
    const card=page.getByRole('listitem').filter({has:page.getByRole('heading',{name:'LOCAL RECORDED REPLAY',exact:true})})
    await card.getByRole('button',{name:'Control și configurare',exact:true}).click()
  } else if (['start','stop','health','draft','approve','rollback','disable'].includes(process.env.RS_CAMERA_TASK)) {
    const card=page.getByRole('listitem').filter({has:page.getByRole('heading',{name:'LOCAL RECORDED REPLAY',exact:true})})
    await card.getByRole('button',{name:'Control și configurare',exact:true}).click()
    await page.getByTestId('control-reason').fill('Licensed local replay: independently reviewed browser configuration')
    if(['start','stop'].includes(process.env.RS_CAMERA_TASK)) {
      await page.getByRole('dialog',{name:'Control cameră',exact:true}).getByRole('button',{name:'Închide',exact:true}).click()
      const control=card.getByRole('region',{name:'Control analytics worker',exact:true})
      if(process.env.RS_CAMERA_TASK==='start') await control.getByLabel('Config local cameras/*.yaml').fill(JSON.parse(process.env.RS_CAMERA_CONFIG).profile)
      const action=process.env.RS_CAMERA_TASK
      const sent=page.waitForResponse(r=>r.request().method()==='POST' && new URL(r.url()).pathname.endsWith('/worker/'+action))
      await control.getByRole('button',{name:action==='start'?'Start':'Stop',exact:true}).click()
      const response=await sent;expect(response.status()).toBe(200)
      fs.writeFileSync(process.env.RS_CAMERA_RESULT,JSON.stringify(await response.json()),{mode:0o600})
    } else if(process.env.RS_CAMERA_TASK==='health') {
      await expect(page.getByRole('dialog',{name:'Control cameră',exact:true}).getByTestId('runtime-state')).toHaveAttribute('data-state',JSON.parse(process.env.RS_CAMERA_CONFIG).expected)
    } else if(process.env.RS_CAMERA_TASK==='draft') {
      await page.getByRole('button',{name:'Ciornă nouă de configurație',exact:true}).click()
      await page.getByLabel('Configurație JSON',{exact:true}).fill('{invalid')
      await page.getByRole('button',{name:'Salvează ca ciornă',exact:true}).click()
      await expect(page.getByText(/JSON invalid/).first()).toBeVisible()
      await page.getByLabel('Configurație JSON',{exact:true}).fill(process.env.RS_CAMERA_CONFIG)
      await page.screenshot({path:process.env.RS_E2E_SCREENSHOT.replace('.png','-editor.png'),fullPage:true})
      const created=page.waitForResponse(r=>r.request().method()==='POST' && new URL(r.url()).pathname.endsWith('/versions'))
      await page.getByRole('button',{name:'Salvează ca ciornă',exact:true}).click()
      const response=await created;expect(response.status()).toBe(201);const value=await response.json()
      const version=page.getByTestId('version-'+value.revision)
      await version.getByRole('button',{name:'Validează',exact:true}).click()
      await version.getByRole('button',{name:'Trimite spre aprobare',exact:true}).click()
      await expect(version.getByTestId('version-status')).toHaveText('Așteaptă aprobare')
      fs.writeFileSync(process.env.RS_CAMERA_RESULT,JSON.stringify(value),{mode:0o600})
    } else if(process.env.RS_CAMERA_TASK==='rollback') {
      const version=page.getByTestId('version-'+process.env.RS_CAMERA_REVISION)
      const rolled=page.waitForResponse(r=>r.request().method()==='POST' && new URL(r.url()).pathname.endsWith('/rollback'))
      await version.getByRole('button',{name:'Revino la această versiune',exact:true}).click()
      expect((await rolled).status()).toBe(200)
      await expect(version.getByTestId('version-status')).toHaveText('Activă')
    } else if(process.env.RS_CAMERA_TASK==='disable') {
      await page.getByRole('button',{name:'Dezactivează',exact:true}).click()
      const disabled=page.waitForResponse(r=>r.request().method()==='POST' && new URL(r.url()).pathname.endsWith('/disable'))
      await page.getByRole('button',{name:'Da, dezactivează',exact:true}).click()
      expect((await disabled).status()).toBe(200)
      await expect(page.getByTestId('runtime-state')).toContainText('Dezactivată')
    } else {
      const version=page.getByTestId('version-'+process.env.RS_CAMERA_REVISION)
      const approved=page.waitForResponse(r=>r.request().method()==='POST' && new URL(r.url()).pathname.endsWith('/approve'))
      await version.getByRole('button',{name:'Aprobă (alt administrator)',exact:true}).click();expect((await approved).status()).toBe(200)
      const activated=page.waitForResponse(r=>r.request().method()==='POST' && new URL(r.url()).pathname.endsWith('/activate'))
      await version.getByRole('button',{name:'Activează',exact:true}).click()
      const response=await activated;expect(response.status()).toBe(200)
      fs.writeFileSync(process.env.RS_CAMERA_RESULT,JSON.stringify(await response.json()),{mode:0o600})
      await expect(version.getByTestId('version-status')).toHaveText('Activă')
    }
  } else if(process.env.RS_CAMERA_TASK==='event') {
    const number=JSON.parse(process.env.RS_CAMERA_CONFIG).event_number
    await page.goto(origin+'/app/alerte/'+number)
    await expect(page.getByText(/\[SYNTHETIC TEST\]/).first()).toBeVisible()
    await expect(page.getByText(/LOCAL RECORDED REPLAY/).first()).toBeVisible()
    await page.waitForFunction(()=>{const v=document.querySelector('video');return v && v.readyState>=2 && v.videoWidth>0 && v.duration>0})
    await page.getByRole('button',{name:'Respinge',exact:true}).click()
    await page.getByLabel('Motiv (obligatoriu)',{exact:true}).fill('SYNTHETIC TEST: configured whole-scene zone; no actual traffic violation')
    await page.getByRole('button',{name:'Continuă: respinge alerta',exact:true}).click()
    const decision=page.waitForResponse(r=>r.request().method()==='POST' && new URL(r.url()).pathname.endsWith('/decision'))
    await page.getByRole('button',{name:'Respinge alerta',exact:true}).click();expect((await decision).status()).toBe(200)
    await expect(page.getByText('Alertă respinsă',{exact:true})).toBeVisible()
  } else {
    const card=page.getByRole('listitem').filter({has:page.getByRole('heading',{name:'LOCAL RECORDED REPLAY',exact:true})})
    await card.getByRole('button',{name:'Detalii live',exact:true}).click()
    const preview=page.getByTestId('camera-live-preview')
    await preview.waitFor()
    await page.waitForFunction(()=>{
      const img=document.querySelector('[data-testid="camera-live-preview"]')
      return img instanceof HTMLImageElement && img.complete && img.naturalWidth>0 && img.dataset.capturedAt
    })
    const before=await preview.getAttribute('data-captured-at')
    await page.waitForFunction(first=>document.querySelector('[data-testid="camera-live-preview"]')?.getAttribute('data-captured-at')!==first,before)
    await expect(page.getByRole('region',{name:'Previzualizare video cu detecții'})).toContainText('RECORDED REPLAY')
  }
  await page.screenshot({path:process.env.RS_E2E_SCREENSHOT,fullPage:true})
  console.log('PASS actual camera browser '+process.env.RS_CAMERA_TASK)
} finally { await browser.close() }
