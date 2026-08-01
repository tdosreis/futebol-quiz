# Google Play — Store Listing & Publishing Checklist

App: **Futebol Quiz BR** · Package: `io.github.tdosreis.futebolquiz`

---

## 1. Store listing text (pt-BR)

**App name** (max 30)
```
Futebol Quiz BR
```

**Short description** (max 80)
```
Teste seus conhecimentos sobre futebol! Perguntas de craques, times e história.
```

**Full description** (max 4000)
```
⚽ Você realmente entende de futebol? Prove no Futebol Quiz BR!

Coloque seu conhecimento à prova com perguntas sobre jogadores, clubes, seleções,
títulos e momentos históricos do esporte mais amado do Brasil.

🏆 O QUE VOCÊ ENCONTRA:
• Perguntas sobre craques, times e história do futebol
• Vários níveis de dificuldade
• Pontuação a cada acerto — tente bater seu recorde
• Jogo rápido, perfeito para qualquer momento do dia
• 100% em português

📵 SEM COMPLICAÇÃO:
• Sem cadastro e sem login
• Sem anúncios
• Não coleta nenhum dado pessoal
• Leve e rápido

Do futebol raiz aos dias atuais — quantas você acerta? Desafie os amigos e descubra
quem é o verdadeiro craque do quiz!
```

**Privacy policy URL**
```
https://tdosreis.github.io/futebol-quiz/privacy.html
```
(after you commit & push privacy.html — verify it returns 200 first)

---

## 2. Graphic assets you must upload

| Asset | Spec | Notes |
|-------|------|-------|
| App icon | 512×512 PNG (32-bit) | You already have icons/icon-512.png |
| Feature graphic | 1024×500 PNG/JPG | Required. Needs to be made. |
| Phone screenshots | 2–8, min 320px, 16:9 or 9:16 | REQUIRED. Capture from your phone/emulator. |
| Tablet screenshots | optional | skip unless targeting tablets |

Tip: take screenshots of the difficulty screen, a question mid-game, and the score screen.

---

## 3. Required questionnaires (App content section)

- **Privacy policy**: URL above
- **Data safety**: "No data collected" / "No data shared" (verified: app has no
  network calls, no analytics, no localStorage — scores are in-memory only)
- **Ads**: No, my app does not contain ads
- **Content rating**: complete IARC questionnaire → will come out "Everyone / Livre"
- **Target audience & content**: 13+ is simplest; avoid the "under 13" (Families) track
  unless you want extra requirements
- **News app**: No
- **Government app**: No
- **Financial features**: No

---

## 4. Asset Links fix (do after upload) — CRITICAL for fullscreen

Play App Signing re-signs the app with Google's key. Add Google's SHA-256 to
assetlinks.json (in the **tdosreis.github.io root repo**, NOT this repo):

Path in root repo: `.well-known/assetlinks.json`
```json
[{
  "relation": ["delegate_permission/common.handle_all_urls"],
  "target": {
    "namespace": "android_app",
    "package_name": "io.github.tdosreis.futebolquiz",
    "sha256_cert_fingerprints": [
      "EB:7E:E9:F6:55:4B:E5:E9:57:8E:A5:94:0E:7E:1C:FC:FD:58:B4:92:A3:8C:98:89:C9:54:94:A3:E2:D2:DD:97",
      "PASTE_GOOGLE_APP_SIGNING_SHA256_HERE"
    ]
  }
}]
```
- First fingerprint = your NEW upload key (for local sideload testing).
- Second = Google's Play App Signing key — the one that matters for the LIVE app;
  get it after upload and replace the placeholder.
- The OLD leaked fingerprint (79:51:D3...) has been removed — that key is dead.
Get Google's fingerprint from: Play Console → Test and release → App integrity →
App signing → "App signing key certificate" SHA-256.

Verify after push: `curl https://tdosreis.github.io/.well-known/assetlinks.json`

---

## 5. Publish order

1. Create app (App name, package `io.github.tdosreis.futebolquiz`, pt-BR, Game, Free, declarations)
2. Upload **`android/app-upload.aab`** (the re-signed bundle) → **Internal testing** first
3. Complete all App content questionnaires + store listing above
4. Select countries (Brasil + others)
5. Install from Internal testing link → confirm it opens FULLSCREEN (no URL bar)
   - if it shows a browser URL bar → the assetlinks.json Google-fingerprint step (section 4) isn't done/propagated
6. **Closed testing gate (personal accounts created after 2023-11-13):**
   run a Closed test with **>=12 testers opted-in for 14 continuous days** before you
   can apply for production access. Recruit ~15 for buffer; the clock only counts days
   with >=12 active testers.
7. Apply for production access -> then promote release to **Production**.

⚠️ Back up `android/futebol-quiz-upload.keystore` + its password before anything else.
   (The old `futebol-quiz.keystore` was leaked/rotated out — do not use it.)

---

## 6. Monetization plan (later — app ships FREE, no ads at launch)

The app is published **Free with no ads** (Data safety / Ads declaration = "No").
Monetization is a later, additive step — no new app or package change needed.

### Recommended path: web ads (Google AdSense) on the site

Because this is a **TWA**, the app is literally your website
(`tdosreis.github.io/futebol-quiz/`) rendered in Chrome. So ads are added to the
**web page**, not to native Android code — they then appear inside the app too.

Steps when you're ready:
1. Apply for **Google AdSense** with the site `tdosreis.github.io` (needs approval;
   easier once the site has real traffic + this privacy policy, which is already live).
2. Add the AdSense script + one or two responsive ad units into `index.html`
   (e.g. a banner between the score bar and the question card, and/or an interstitial
   on the "results" screen between rounds).
3. Redeploy GitHub Pages — the live TWA picks it up automatically (no Play re-upload,
   no version bump needed, since content is served from the web).

### ⚠️ Policy caveats — read before enabling ads
- **AdSense is designed for websites.** A TWA renders a real site, so web visitors are
  clearly fine; ads shown to *app-wrapper* traffic sit in a gray area of AdSense policy.
  The clean-compliance alternative for an app is **AdMob**, but AdMob needs *native*
  ad units — not available in a pure TWA without adding native code. Start with AdSense
  on the web; if Play/AdSense ever flags it, migrate to a native/AdMob build.
- **You MUST update Play declarations when ads go live:**
  - App content -> **Ads = "Yes, my app contains ads"**
  - Data safety -> revisit (AdSense may collect device/usage data for ad personalization)
  - Update `privacy.html` to disclose third-party ads + data use (AdSense requires this)
- Keep ads **non-intrusive** (no ads over answer buttons / covering gameplay) — Play
  rejects apps with disruptive ads.

### Alternative: in-app purchase to remove ads / unlock content
- A Free app can sell IAPs, but in a TWA this needs the **Play Billing + Digital Goods
  API** wired into the web app (Bubblewrap supports a Play Billing feature flag).
  More setup than AdSense; consider only after ad revenue proves demand.

### If you ever want a true PAID (pay-to-download) app
- Not possible to convert this Free app. Publish a separate **"Futebol Quiz Pro"** with
  a new package id (e.g. `io.github.tdosreis.futebolquizpro`) set to Paid. Low priority.
