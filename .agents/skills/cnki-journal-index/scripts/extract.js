// CNKI 期刊收录查询 — 提取期刊评价数据
// 参考: ../../references/cnki-common-selectors.md

() => {
  const body = document.body.innerText;

  // 刊名
  const titleEl = document.querySelector('h3.titbox, h3.titbox1');
  const titleText = titleEl?.innerText?.trim() || '';
  const titleParts = titleText.split('\n').map(s => s.trim()).filter(Boolean);
  const nameCN = titleParts[0] || '';
  const nameEN = titleParts[1] || '';

  // 收录标签
  const tagText = body.match(/Chinese.*?\n\n([\s\S]*?)\n\n基本信息/)?.[1]
    || body.match(new RegExp(nameCN + '[\\s\\S]*?\\n\\n([\\s\\S]*?)\\n\\n基本信息'))?.[1]
    || '';
  const knownTags = ['北大核心','CSSCI','CSCD','SCI','EI','CAS','JST','WJCI','AMI','Scopus','卓越期刊','网络首发'];
  const indexedIn = knownTags.filter(tag => tagText.includes(tag) || body.includes(tag));

  // 基本信息
  const sponsor = body.match(/主办单位[：:]\s*(.+?)(?=\n)/)?.[1] || '';
  const frequency = body.match(/出版周期[：:]\s*(\S+)/)?.[1] || '';
  const issn = body.match(/ISSN[：:]\s*(\S+)/)?.[1] || '';
  const cn = body.match(/CN[：:]\s*(\S+)/)?.[1] || '';

  // 出版信息
  const collection = body.match(/专辑名称[：:]\s*(.+?)(?=\n)/)?.[1] || '';
  const paperCount = body.match(/出版文献量[：:]\s*(.+?)(?=\n)/)?.[1] || '';

  // 评价指标
  const impactComposite = body.match(/复合影响因子[：:]\s*([\d.]+)/)?.[1] || '';
  const impactComprehensive = body.match(/综合影响因子[：:]\s*([\d.]+)/)?.[1] || '';

  // 更多介绍
  const moreBtn = Array.from(document.querySelectorAll('a')).find(a => a.innerText?.includes('更多介绍'));
  const hasMoreIntro = !!moreBtn;

  return {
    nameCN, nameEN, indexedIn,
    sponsor, frequency, issn, cn,
    collection, paperCount,
    impactComposite, impactComprehensive,
    hasMoreIntro,
    rawTagText: tagText.substring(0, 200)
  };
}
