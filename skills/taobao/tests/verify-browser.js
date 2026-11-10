async (page, read) => {
  const tab = await page.context().newPage();
  const checks = [];
  let fixture = '';
  const check = (condition, name) => {
    if (!condition) throw new Error(name);
    checks.push(name);
  };
  try {
    await tab.route('**/*', route => route.fulfill({
      status: 200,
      contentType: route.request().resourceType() === 'image' ? 'image/svg+xml' : 'text/html; charset=utf-8',
      body: route.request().resourceType() === 'image' ? `<svg xmlns="http://www.w3.org/2000/svg" width="${route.request().url().includes('small') ? 80 : 750}" height="${route.request().url().includes('small') ? 80 : 900}"></svg>` : fixture
    }));
    fixture = '<title>測試商品</title><a href="https://i.taobao.com/my_itaobao">我的淘宝</a><h1>用户评价</h1><span class="mainTitle--test">雙卡測試商品</span><div class="isSelected--test">32GB × 2</div><div class="highlightPrice--test">￥14599</div><div class="emphasisParamsInfoItem--test">1年 质保期</div><div class="generalParamsInfoItem--test">型號 V100</div><div class="comment-item" data-score="1"><p class="comment-con">包裝破損</p><span>customer-private-name</span></div><div class="detail--test"><img src="https://img.alicdn.com/a.svg"><img src="https://img.alicdn.com/a.svg"><img src="https://img.alicdn.com/b.svg"></div>';
    await tab.goto('https://item.taobao.com/item.htm?id=123&skuId=456');
    const first = await read(tab, {limit: 1});
    check(first.login === 'unknown', '我的淘寶連結不誤判成已登入');
    check(first.title === '雙卡測試商品', '商品標題優先於評價標題');
    check(first.product_id === '123' && first.sku_id === '456' && first.selected_options[0] === '32GB × 2', '保留所選款式');
    check(first.price_text === '￥14599' && first.warranty === '1年 质保期', '價格及保固讀回');
    check(first.images.length === 1 && first.image_total_visible === 2 && first.next_offset === 1, '圖片去重及分頁');
    const second = await read(tab, {offset: 1, limit: 1});
    check(second.images[0].url !== first.images[0].url && second.next_offset === null, '圖片續頁不重複');
    check(first.reviews[0].text === '包裝破損' && !JSON.stringify(first).includes('customer-private-name'), '評價不帶帳戶姓名');
    check(first.price_status === 'visible_page_sku_unverified', '頁面價格不假稱已證明對應款式');
    fixture = '<a class="site-nav-login-info-nick">private-account</a><input type="password">';
    await tab.goto('https://item.taobao.com/item.htm?id=123');
    const login = await read(tab);
    check(login.status === 'login_required' && !JSON.stringify(login).includes('private-account'), '登入表單優先且不輸出帳戶');
    fixture = '<a class="site-nav-login-info-nick">private-account</a><p>请完成验证</p>';
    await tab.goto('https://item.taobao.com/item.htm?id=123');
    check((await read(tab)).status === 'verification_required', '驗證與登出分開');
    fixture = '<a class="site-nav-login-info-nick">private-account</a><span class="mainTitle--test">可讀商品</span>';
    await tab.goto('https://item.taobao.com/item.htm?id=123');
    const account = await read(tab);
    check(account.login === 'logged_in' && !JSON.stringify(account).includes('private-account') && account.price_text === null, '已登入與未知價格分開');
    fixture = '<a href="https://item.taobao.com/item.htm?id=123" style="display:block;width:10px;height:10px"></a><article class="card"><a href="https://item.taobao.com/item.htm?id=123&skuId=456&tracking=secret" title="搜尋商品">搜尋商品</a><span class="price">￥100</span></article><a href="https://item.taobao.com/item.htm?id=123">重複</a><a href="https://item.taobao.com.evil.test/item.htm?id=9">假網站</a>';
    await tab.goto('https://s.taobao.com/search?q=test');
    const search = await read(tab);
    check(search.status === 'search_results' && search.products.length === 1 && search.products[0].url.endsWith('id=123&skuId=456'), '搜尋去重與保留款式、去除追蹤參數');
    fixture = '<div class="sku-name">京東測試</div><div class="summary-price"><div class="p-price">￥200</div></div><ul class="p-parameter"><li>記憶體 64GB</li></ul>';
    await tab.goto('https://item.jd.com/987.html');
    const jd = await read(tab);
    check(jd.platform === 'jd' && jd.product_id === '987' && jd.price_text === '￥200' && jd.parameters[0] === '記憶體 64GB', '京東商品讀取');
    fixture = '<div class="sku--test"><img src="https://img.alicdn.com/small.svg" height="80" width="80"></div>';
    await tab.goto('https://item.taobao.com/item.htm?id=123');
    check((await read(tab)).images[0]?.category === 'sku', '款式縮圖不被排除');
    await tab.evaluate(() => {
      document.body.replaceChildren();
      const container = document.createElement('div');
      container.className = 'detail--test';
      for (let i = 0; i < 501; i++) {
        const img = document.createElement('img');
        img.setAttribute('data-src', `https://img.alicdn.com/cap-${i}.svg`);
        Object.defineProperty(img, 'naturalWidth', {value: 750});
        Object.defineProperty(img, 'naturalHeight', {value: 900});
        container.append(img);
      }
      document.body.append(container);
    });
    const capped = await read(tab, {offset: 490, limit: 20});
    check(capped.images.length === 10 && capped.images_truncated === true && capped.next_offset === null, '圖片達上限明確回報截斷');
    return {passed: checks.length, checks, network: '所有測試請求均由本機攔截，不送網站、不登入'};
  } finally {
    await tab.close();
  }
}
