// Run with playwright-cli run-code in a fresh profile opened on the expansion preview.
async (page) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.emulateMedia({reducedMotion:'reduce'});
  await page.setViewportSize({width:390,height:844});
  const assert = (condition,message) => { if (!condition) throw Error(message); };
  const setup = async () => {
    if (await page.locator('#start-match').isVisible()) return;
    await page.locator('#menu-button').click();
    await page.locator('#new-game-button').click();
  };
  const start = async () => {
    await page.locator('#start-match').click();
    await page.waitForFunction(() => view && !busy && !document.querySelector('#detail-dialog').open);
  };
  const save = async (name) => {
    await page.locator('#deck-name').fill(name);
    await page.locator('#save-deck').click();
    await page.getByRole('status').filter({hasText:name}).waitFor();
  };
  await page.waitForFunction(() => growthCatalog && !busy);
  const artworkFailures = await page.evaluate(async () => {
    // Use the playable catalog, including signatures that don't appear in the editor.
    const illustrated = growthCatalog.cards.filter(c =>
      c.card_type !== 'Hero' ? c.card_id < 64000 || c.card_type === 'Item' : [10022,10032].includes(c.card_id));
    if (illustrated.length !== 65) return [`Expected 65 illustrated cards, found ${illustrated.length}`];
    const failures = await Promise.all(illustrated.map(async card => {
      const art = new Image();
      art.src = image(card.card_id);
      if (!art.src.endsWith(`/assets/cards/${card.card_id}.webp`)) return card.card_name.schinese;
      return art.decode().then(() => null, () => card.card_name.schinese);
    }));
    return failures.filter(Boolean);
  });
  assert(!artworkFailures.length, `Missing original art: ${artworkFailures.join(', ')}`);
  await setup();
  assert(await page.locator('input[value=saved]').isDisabled(), 'Saved opponent needs a red deck');
  await page.locator('input[value=equipment]').check();
  await start();
  assert(await page.evaluate(() => view.matchup.opponent === '装备成长'), 'Equipment preset starts a match');
  const preset = await page.evaluate(() => api(`/api/games/${gameId}/export`));
  assert(preset.deck_config.opponent.items.includes(65017), 'Actual preset uses the equipment deck');

  await setup();
  await page.locator('#open-deck-library').click();
  await page.locator('[data-new-deck=green]').click();
  const sproutArt = page.locator('.deck-row').filter({hasText:'共生幼苗'}).locator('img');
  await sproutArt.scrollIntoViewIfNeeded();
  await sproutArt.evaluate(img => img.decode());
  assert(await sproutArt.evaluate(img => img.src.endsWith('/cards/61008.webp')), 'Deck editor uses the matched original art');
  await page.locator('[data-deck-id="61007"][data-delta="-1"]').click();
  assert(await page.locator('#save-deck').isDisabled(), 'Incomplete deck cannot be saved');
  await page.locator('[data-deck-id="61007"][data-delta="1"]').click();
  await save('古林守备');
  await page.locator('#copy-deck').click();
  await page.locator('[data-deck-id="61007"][data-delta="-1"]').click();
  await page.locator('[data-deck-id="61008"][data-delta="1"]').click();
  await save('林线推进');
  await page.locator('#back-to-decks').click();
  await page.locator('[data-new-deck=red]').click();
  await save('赤铁前线');
  await page.locator('#back-to-decks').click();
  await page.screenshot({path:'output/deck-lobby/library.png'});
  await page.locator('#deck-to-lobby').click();
  await page.locator('#match-deck').selectOption({label:'古林守备'});
  await page.locator('input[value=saved]').check();
  assert(await page.evaluate(() => {
    const decks=readLibrary();
    const original=decks.find(d=>d.name==='古林守备');
    const copy=decks.find(d=>d.name==='林线推进');
    return original.id!==copy.id && original.ordinary.filter(id=>id===61007).length===2
      && copy.ordinary.filter(id=>id===61007).length===1
      && copy.ordinary.filter(id=>id===61008).length===3;
  }), 'Copy can be edited independently');
  const launch = await page.locator('#start-match').boundingBox();
  assert(launch.width > 150 && launch.height < 55, 'Primary action fits on one line on mobile');
  await page.screenshot({path:'output/deck-lobby/setup.png'});
  await start();
  assert(await page.evaluate(() => view.matchup.player==='古林守备' && view.matchup.opponent==='赤铁前线'),
    'Selected green deck and random eligible red deck enter battle');
  await page.reload();
  await page.waitForFunction(() => view && !busy);
  assert(await page.evaluate(() => readLibrary().length === 3 && view.matchup.opponent==='赤铁前线'),
    'Library and actual opponent survive reload');
  const snapshot = await page.evaluate(() => api(`/api/games/${gameId}/export`));
  assert(snapshot.deck_config.opponent.name === '赤铁前线' && snapshot.deck_config.opponent.ordinary.length===21,
    'Replay snapshots the selected saved opponent');

  // Choose a known draw to inspect the three new art cards through their real hand entries.
  await page.evaluate(async () => applyPacket(await api('/api/games',{seed:27,deck_config:{
    ...growthCatalog.expansionDeck,experiment:'combined'}})));
  for (const [id,kind] of [[61007,'unit'],[62013,'spell'],[65011,'item']]) {
    if (kind==='item') await page.locator('#tab-items').click();
    await page.locator(`.hand-card[data-card="${id}"]`).first().click();
    const art=page.locator('.full-face img');
    await art.evaluate(img=>img.decode());
    assert(await art.evaluate((img,cid)=>img.naturalWidth>0 && img.src.endsWith(`/cards/${cid}.webp`),id),
      `Original card art and frame load for ${kind}`);
    await page.screenshot({path:`output/deck-lobby/${kind}.png`});
    await page.locator('#close-detail').click();
  }
  for (const width of [360,390,1024]) {
    await page.setViewportSize({width,height:844});
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth), `Board overflow at ${width}px`);
  }
  assert(errors.length===0,errors.join('\n'));
  return ['65 original artworks', 'deck editor art', 'equipment preset', 'independent copy',
    'random saved opponent', 'reload', 'replay snapshot', 'three framed cards'];
}
