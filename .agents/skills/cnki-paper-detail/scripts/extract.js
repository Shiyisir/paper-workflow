// CNKI 论文详情提取 — 提取完整元数据
// 参考: ../../references/cnki-common-selectors.md

() => {
  const brief = document.querySelector('.brief');
  if (!brief) return { error: 'Paper detail section (.brief) not found' };

  // 标题
  const title = brief.querySelector('h1')?.innerText?.trim()
    ?.replace(/\s*附视频\s*$/, '')
    ?.replace(/\s*网络首发\s*$/, '');

  // 作者
  const authorH3s = brief.querySelectorAll('h3.author');
  const authorSection = authorH3s[0];
  const authors = [];
  if (authorSection) {
    authorSection.querySelectorAll('a').forEach(a => {
      const name = a.innerText?.replace(/\d+$/, '').trim();
      const supMatch = a.innerText?.match(/(\d+)$/);
      authors.push({ name, affiliationNum: supMatch ? supMatch[1] : '' });
    });
  }

  // 机构
  const affiliations = [];
  if (authorH3s.length > 1) {
    authorH3s[1].querySelectorAll('a').forEach(a => {
      affiliations.push(a.innerText?.trim());
    });
  }

  // 摘要/关键词/基金/分类
  const abstract = document.querySelector('.abstract-text')?.innerText?.trim() || '';
  const keywordsP = document.querySelector('p.keywords');
  const keywords = keywordsP
    ? Array.from(keywordsP.querySelectorAll('a')).map(a => a.innerText?.replace(/;$/, '').trim())
    : [];
  const fund = document.querySelector('p.funds')?.innerText?.trim() || '';
  const classification = document.querySelector('.clc-code')?.innerText?.trim() || '';

  // 期刊/出版信息
  const journal = document.querySelector('.doc-top')?.querySelector('a')?.innerText?.trim() || '';
  const pubInfo = document.querySelector('.head-time')?.innerText?.trim() || '';
  const isOnlineFirst = !!brief.querySelector('.icon-shoufa');

  // 目录
  const catalogList = document.querySelector('.catalog-list, .catalog-listDiv');
  const toc = catalogList?.innerText?.trim() || '';

  // 引用网络
  const citationTabs = document.querySelectorAll('ul.module-tab.tpl_lieteratures li');
  const citationInfo = {};
  citationTabs.forEach(li => {
    const id = li.getAttribute('data-id');
    const text = li.innerText?.trim();
    const countMatch = text.match(/(\d+)/);
    if (id) {
      citationInfo[id] = {
        label: text.replace(/\d+/, '').trim(),
        count: countMatch ? parseInt(countMatch[1]) : 0
      };
    }
  });

  return {
    title, authors, affiliations,
    abstract, keywords, fund, classification,
    journal, pubInfo, isOnlineFirst, toc, citationInfo
  };
}
