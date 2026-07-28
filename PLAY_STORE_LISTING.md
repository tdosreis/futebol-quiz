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

1. Create app (App name, package, pt-BR, Game, Free, declarations)
2. Upload `android/app-release-bundle.aab` → **Internal testing** first
3. Complete all App content questionnaires + store listing above
4. Select countries (Brasil + others)
5. Install from Internal testing link → confirm it opens FULLSCREEN (no URL bar)
6. If fullscreen works → promote release to **Production**

⚠️ Back up `android/futebol-quiz.keystore` before anything else.
