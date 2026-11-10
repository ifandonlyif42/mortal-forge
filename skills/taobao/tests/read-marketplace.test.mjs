import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import test from 'node:test';
import vm from 'node:vm';

const source = await readFile(new URL('../scripts/read-marketplace.js', import.meta.url), 'utf8');
const read = vm.runInNewContext(`(${source})`, {URL, Date, Set});

test('拒絕非法分頁且不觸碰瀏覽器', async () => {
  for (const request of [{limit: 0}, {limit: 21}, {offset: -1}, {offset: 501}, {offset: 1.5}, {limit: '10'}]) {
    await assert.rejects(read({}, request), /單批數量/);
  }
});

test('拒絕非購物網站、假網域與不安全協定', async () => {
  for (const url of ['https://example.com/', 'https://item.taobao.com.evil.test/', 'http://item.taobao.com/item.htm?id=1', 'file:///tmp/a', 'about:blank']) {
    const result = await read({url: () => url, evaluate: () => {throw Error('不應讀取頁面');}});
    assert.equal(result.status, 'unsupported_page');
  }
});

test('保留頁面錯誤，不偽裝成登出', async () => {
  await assert.rejects(read({url: () => 'https://item.taobao.com/item.htm?id=1', evaluate: async () => {throw Error('browser unavailable');}}), /browser unavailable/);
});
