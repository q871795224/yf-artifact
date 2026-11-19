// Run with playwright-cli run-code --filename scripts/check_growth_prototype.js.
async (page) => {
  const checks = [], errors = [];
  const check = (ok, label) => { if (!ok) throw new Error(label); checks.push(label); };
  page.on('pageerror', error => errors.push(error.message));
  await page.emulateMedia({reducedMotion:'reduce'});
  await page.setViewportSize({width:390,height:844});
  await page.waitForFunction(() => growthCatalog && (!busy || document.querySelector('#recover-new')));
  if (await page.locator('#recover-new').isVisible()) {
    await page.locator('#recover-new').click();
    await page.waitForFunction(() => view && !busy);
  }
  await page.evaluate(async () => {
    closeDetail();
    document.querySelector("#scene-dialog").close();
    const packet = await api('/api/games',{seed:13,deck_config:growthCatalog.defaultDeck});
    rememberId(packet.game_id);
    await applyPacket(packet);
  });
  check(await page.locator('.cell').count() === 40,'5×8 board');
  check(await page.locator('.cell.hero').count() === 2,'One opening hero per side');
  check(await page.locator('.level-badge').count() === 2,'Hero level badges');
  check((await page.locator('#mana-value').innerText()).replace(/\s/g,'') === '1/1','One opening mana');
  check(await page.evaluate(() => view.forts.every(f => f.col === 2 && f.row === (f.team === 0 ? 6 : 1) && f.reach === 1)), 'Towers move forward one rank and cover eight neighbors');
  check(await page.locator('#global-skill').isDisabled(),'Two-mana tactics are unavailable in round one');
  check(await page.locator('.hand-card').count() === 5,'Five starting ordinary cards');
  await page.getByRole('button',{name:'对局菜单',exact:true}).click();
  await page.locator('[data-menu="deck"]').click();
  check(await page.locator('.deck-row').count() === 38,'All green ordinary cards and 22 item types in deck builder');
  await page.locator('[data-deck-id="61007"][data-delta="-1"]').click();
  check(await page.locator('#save-deck').isDisabled(),'Incomplete deck cannot be saved');
  await page.locator('[data-deck-id="61007"][data-delta="1"]').click();
  await page.locator('#save-deck').click();
  check(await page.evaluate(()=>JSON.parse(localStorage.getItem(deckStorageKey)).ordinary.length === 21),'Deck saved with 21 selected cards plus nine signatures');
  await page.locator('#close-detail').click();
  const before = await page.evaluate(()=>({mana:view.mana,version:view.version,hand:view.hand.length}));
  await page.locator('.hand-card').first().click();
  await page.locator('#reforge-card').click();
  await page.waitForFunction(v=>!busy && view.version === v+1,before.version);
  check(await page.evaluate(b=>view.mana === b.mana && view.hand.length === b.hand,before),'Reforge spends one action and zero mana, preserving hand size');
  await page.locator('#tab-items').click();
  await page.locator('.hand-card').first().click();
  check(await page.locator('#reforge-card').count() === 0,'Items have no reforge control');
  await page.locator('#close-detail').click();
  await page.locator('#tab-cards').click();
  await page.locator('.cell.hero[data-team="ally"]').first().click();
  check(await page.locator('.reachable').count()>0,'Hero can select legal movement');
  await page.locator('.reachable').first().click();
  await page.waitForFunction(()=>!busy);
  // Exercise real UI transitions through reinforcements, combat and experience.
  for (let n=0;n<90;n++) {
    if (await page.evaluate(()=>view.round>=4 || view.phase==='finished')) break;
    await page.locator('#pass-button').click();
    if (await page.locator('#finish-shop').isVisible()) {
      check(await page.locator('.shop-offer').count() === 3,'Three market sources are visible');
      await page.locator('#finish-shop').click();
    }
    await page.waitForFunction(()=>!busy);
  }
  check(await page.evaluate(()=>view.round>=4),'Round transitions reach the growth phase');
  check(await page.evaluate(()=>view.heroes.length===6 && view.heroes.some(h=>h.xp>0)),'Six heroes retain experience through combat');
  const saved = await page.evaluate(()=>({version:view.version,round:view.round,heroes:view.heroes,gold:view.gold}));
  await page.reload();
  await page.waitForFunction(()=>view && !busy);
  check(await page.evaluate(s=>JSON.stringify({version:view.version,round:view.round,heroes:view.heroes,gold:view.gold})===JSON.stringify(s),saved),'Refresh restores the same round, heroes, experience and gold');
  for (const [width,height] of [[390,844],[360,740],[768,1024]]) {
    await page.setViewportSize({width,height});
    check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`No horizontal overflow at ${width}×${height}`);
  }
  await page.setViewportSize({width:390,height:844});
  await page.locator('#menu-button').click();
  await page.locator('[data-menu="roster"]').click();
  await page.locator('.roster-unit').first().click();
  check((await page.locator('#detail-body').innerText()).includes('成长（攻/甲/血）'),'Hero details show all three panels');
  await page.locator('#close-detail').click();
  await page.evaluate(()=>Promise.all([...document.images].map(img=>img.decode().catch(()=>{}))));
  check(await page.evaluate(()=>[...document.images].every(i=>i.naturalWidth>0)),'All displayed images load');
  check(errors.length===0,'No browser JavaScript errors');
  return {checks,errors,mode:await page.evaluate(()=>window.ARTIFACT_RUNTIME),round:await page.evaluate(()=>view.round)};
}
