#!/usr/bin/env node
'use strict';
const path = require('path');
const HOME = process.env.HOME;

async function main() {
  const { TwaManifest, TwaGenerator, Config } = require('@bubblewrap/core');

  const outputDir = __dirname;

  const config = new Config(
    path.join(HOME, 'android-jdk17/Contents/Home'),
    path.join(HOME, 'android-sdk')
  );

  console.log('Fetching web manifest from GitHub Pages…');
  const twaManifest = await TwaManifest.fromWebManifest(
    'https://tdosreis.github.io/futebol-quiz/manifest.json'
  );

  // Override fields that init wizard would ask about
  twaManifest.packageId           = 'io.github.tdosreis.futebolquiz';
  twaManifest.name                = 'Futebol Quiz BR';
  twaManifest.launcherName        = 'Futebol Quiz';
  twaManifest.appVersionName      = '1.0.0';
  twaManifest.appVersionCode      = 1;
  twaManifest.signingKey          = {
    path:  path.join(outputDir, 'futebol-quiz.keystore'),
    alias: 'futebol-quiz',
  };
  twaManifest.fullScopeUrl        = new URL('https://tdosreis.github.io/futebol-quiz/');
  twaManifest.startUrl            = '/futebol-quiz/';
  twaManifest.enableNotifications          = false;
  twaManifest.enableSiteSettingsShortcut   = true;
  twaManifest.isChromeOSOnly      = false;
  twaManifest.isMetaQuest         = false;
  twaManifest.fingerprints        = [];
  twaManifest.shortcuts           = [];
  twaManifest.features            = {};
  twaManifest.alphaDependencies   = { enabled: false };
  twaManifest.minSdkVersion       = 19;

  await twaManifest.saveToFile(path.join(outputDir, 'twa-manifest.json'));
  console.log('✓ twa-manifest.json written');

  console.log('Generating Android project…');
  const generator = new TwaGenerator();
  await generator.createTwaProject(outputDir, twaManifest, config);
  console.log('✓ Android project generated in', outputDir);
}

main().catch(err => {
  console.error('FAILED:', err.message);
  console.error(err.stack);
  process.exit(1);
});
