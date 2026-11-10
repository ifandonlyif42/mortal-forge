async (page, request = {}) => {
  const offset = request.offset ?? 0;
  const limit = request.limit ?? 10;
  if (!Number.isInteger(offset) || offset < 0 || offset > 500 ||
      !Number.isInteger(limit) || limit < 1 || limit > 20) {
    throw new Error('圖片起點須為 0 至 500，單批數量須為 1 至 20');
  }
  const hosts = new Set(['item.taobao.com', 'detail.tmall.com', 'www.taobao.com',
    's.taobao.com', 'login.taobao.com', 'login.tmall.com', 'login.m.taobao.com',
    'item.m.taobao.com', 'new.m.taobao.com', 'www.jd.com', 'search.jd.com',
    'item.jd.com', 'passport.jd.com']);
  const url = new URL(page.url());
  if (url.protocol !== 'https:' || !hosts.has(url.hostname)) {
    return {status: 'unsupported_page', message: '請先在原瀏覽器開啟淘寶、天貓或京東頁面；不會另開登入'};
  }
  const result = await page.evaluate(({offset, limit}) => {
    const clean = (value, max = 500) => String(value ?? '').replace(/\s+/g, ' ').trim().slice(0, max);
    const visible = el => !!el && el.getClientRects().length > 0;
    const nodes = selector => Array.from(document.querySelectorAll(selector)).filter(visible);
    const first = selector => selector.split(',').map(part => nodes(part).map(el => clean(el.innerText || el.getAttribute('content'))).find(Boolean)).find(Boolean) || null;
    const body = document.body?.innerText || '';
    const current = new URL(location.href);
    const platform = current.hostname.endsWith('.jd.com') ? 'jd' : 'taobao';
    const blocked = nodes('iframe').some(el => /captcha|nocaptcha|punish|verify/.test(el.src)) ||
      /滑动验证|拖动滑块|请完成验证|訪問過於頻繁|访问过于频繁/.test(body);
    const loginForm = nodes('input[type="password"], #J_LoginBox, [class*="login-box"], [class*="loginBox"]').length > 0;
    const loginHost = /^(login\.|passport\.)/.test(current.hostname);
    const account = nodes('.site-nav-login-info-nick, a[href*="i.taobao.com/my_itaobao"], #ttbar-login .nickname')
      .some(el => clean(el.innerText) && !/我的淘宝|我的淘寶|登录|登入|注册/.test(el.innerText));
    const login = blocked ? 'verification_required' : loginHost || loginForm ? 'login_required' : account ? 'logged_in' : 'unknown';
    if (blocked || loginHost || loginForm) {
      return {status: login, platform, login, message: blocked ? '頁面要求人工驗證，請在原瀏覽器完成' : '原瀏覽器目前要求登入；請在此頁完成掃碼'};
    }
    const productHost = ['item.taobao.com', 'detail.tmall.com', 'item.m.taobao.com', 'new.m.taobao.com'].includes(current.hostname);
    const productId = productHost ? current.searchParams.get('id') : platform === 'jd' && current.hostname === 'item.jd.com' ? current.pathname.match(/^\/(\d+)\.html$/)?.[1] : null;
    const canonical = productId ? platform === 'jd' ? `https://item.jd.com/${productId}.html` :
      `https://${current.hostname}/item.htm?id=${productId}${current.searchParams.has('skuId') ? `&skuId=${encodeURIComponent(current.searchParams.get('skuId'))}` : ''}` : null;
    const title = first('[class*="mainTitle"], [class*="ItemTitle"], [class*="itemTitle"], .sku-name, #J_Title h3, h1') || clean(document.title);
    const selected = [...new Set(nodes('[class*="isSelected"], [class*="valueItem"][aria-checked="true"], #choose-attrs .selected, .tb-selected')
      .map(el => clean(el.innerText)).filter(Boolean))].slice(0, 20);
    const priceText = first('[class*="highlightPrice"], [class*="priceText"], [class*="originPrice"] ~ [class*="price"], .summary-price .p-price, .tb-rmb-num');
    const parameters = [...new Set(nodes('[class*="generalParamsInfoItem--"], [class*="emphasisParamsInfoItem--"], [class*="BasicContent"], [class*="basicContent"], [class*="paramItem"], .p-parameter li, .Ptable-item dl, #attributes li')
      .map(el => clean(el.innerText, 600)).filter(Boolean))].slice(0, 100);
    const reviews = nodes('[class*="Comment--"], [class*="commentItem"], [class*="reviewItem"], .comment-item').slice(0, 20).map(el => ({
      text: clean(el.querySelector('[class*="content"], [class*="Content"], .comment-con')?.innerText, 1200) || null,
      rating: el.getAttribute('data-score') || null
    })).filter(item => item.text);
    const images = [];
    const seen = new Set();
    let imagesTruncated = false;
    for (const img of document.images) {
      const src = img.currentSrc || img.getAttribute('data-src') || img.src;
      if (!src || seen.has(src) || !img.naturalWidth || !img.naturalHeight) continue;
      let parsed;
      try { parsed = new URL(src, location.href); } catch { continue; }
      if (parsed.protocol !== 'https:' || !/(^|\.)(alicdn\.com|360buyimg\.com|jd\.com)$/.test(parsed.hostname)) continue;
      const area = img.closest('[class*="sku"], [class*="Sku"], [class*="review"], [class*="Review"], [class*="comment"], [class*="detail"], [class*="Detail"]');
      const group = String(area?.className || '');
      const category = /sku/i.test(group) ? 'sku' : /review|comment/i.test(group) ? 'review' : /detail/i.test(group) ? 'detail' : 'gallery';
      if (!['sku', 'review'].includes(category) && img.naturalWidth < 400 && img.naturalHeight < 400) continue;
      if (images.length >= 500) {
        imagesTruncated = true;
        break;
      }
      seen.add(src);
      images.push({url: parsed.href, category, width: img.naturalWidth, height: img.naturalHeight});
    }
    const products = [];
    const productSeen = new Set();
    if (!productId) {
      for (const anchor of document.querySelectorAll('a[href]')) {
        if (!visible(anchor)) continue;
        let u;
        try { u = new URL(anchor.href); } catch { continue; }
        if (u.protocol !== 'https:') continue;
        const id = ['item.taobao.com', 'detail.tmall.com'].includes(u.hostname) ? u.searchParams.get('id') :
          u.hostname === 'item.jd.com' ? u.pathname.match(/^\/(\d+)\.html$/)?.[1] : null;
        const key = `${u.hostname}:${id}`;
        if (!id || productSeen.has(key)) continue;
        const card = anchor.closest('[class*="Card"], [class*="card"], .gl-item, li, article') || anchor;
        const cardTitle = clean(anchor.getAttribute('title') || card.querySelector('img')?.alt || anchor.innerText, 300);
        if (!cardTitle) continue;
        productSeen.add(key);
        const productUrl = u.hostname === 'item.jd.com' ? `${u.origin}${u.pathname}` : `${u.origin}${u.pathname}?${new URLSearchParams({id, ...(u.searchParams.has('skuId') ? {skuId: u.searchParams.get('skuId')} : {})})}`;
        products.push({title: cardTitle, url: productUrl,
          price_text: clean(card.querySelector('[class*="price"], .p-price')?.innerText, 100) || null});
        if (products.length >= limit) break;
      }
    }
    return {status: productId ? 'product' : products.length ? 'search_results' : 'page_unrecognized', platform, login,
      source_url: canonical, product_id: productId, sku_id: current.searchParams.get('skuId'), title,
      selected_options: selected, price_text: priceText, price_status: priceText ? 'visible_page_sku_unverified' : 'not_found',
      parameters, parameter_status: parameters.length ? 'visible_text' : 'not_found_read_images',
      reviews, review_status: reviews.length ? 'visible_only_unclassified' : 'not_loaded', products,
      images: images.slice(offset, offset + limit), image_total_visible: images.length,
      images_truncated: imagesTruncated,
      next_offset: offset + limit < images.length ? offset + limit : null,
      images_status: 'urls_only_not_visually_verified',
      warranty: parameters.find(value => /质保|保固|保修/.test(value)) || null,
      notice: '僅讀目前頁面；未載入不等於不存在。圖片尚未讀圖，價格與規格都是賣家頁面宣稱。'};
  }, {offset, limit});
  return {...result, observed_at: new Date().toISOString()};
}
