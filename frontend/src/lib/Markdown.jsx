// Small, safe Markdown renderer for the Project Manager's documents
// (headings, paragraphs, lists, tables, quotes, bold, inline code). Builds React
// elements directly, so no HTML from a document is ever injected into the page.

function inline(text, key = 0) {
  const parts = [];
  const re = /(\*\*[^*]+\*\*|`[^`]+`)/g;
  let last = 0;
  let m;
  let i = 0;
  while ((m = re.exec(text))) {
    if (m.index > last) parts.push(text.slice(last, m.index));
    const t = m[0];
    parts.push(
      t.startsWith('**') ? <strong key={`${key}-${i++}`}>{t.slice(2, -2)}</strong> : <code key={`${key}-${i++}`}>{t.slice(1, -1)}</code>,
    );
    last = m.index + t.length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts;
}

const cells = (line) => line.trim().replace(/^\||\|$/g, '').split('|').map((c) => c.trim());

export default function Markdown({ text }) {
  const lines = (text ?? '').replace(/\r/g, '').split('\n');
  const out = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) {
      i += 1;
      continue;
    }
    const h = line.match(/^(#{1,3})\s+(.*)$/);
    if (h) {
      const Tag = `h${h[1].length}`;
      out.push(<Tag key={i}>{inline(h[2], i)}</Tag>);
      i += 1;
      continue;
    }
    if (line.trim().startsWith('|') && lines[i + 1]?.match(/^\s*\|?\s*:?-{3,}/)) {
      const head = cells(line);
      const rows = [];
      i += 2;
      while (i < lines.length && lines[i].trim().startsWith('|')) rows.push(cells(lines[i++]));
      out.push(
        <div className="table-wrap" key={`t${i}`}>
          <table className="table">
            <thead>
              <tr>{head.map((c, j) => <th key={j}>{inline(c, j)}</th>)}</tr>
            </thead>
            <tbody>
              {rows.map((r, k) => (
                <tr key={k}>{r.map((c, j) => <td key={j}>{inline(c, `${k}${j}`)}</td>)}</tr>
              ))}
            </tbody>
          </table>
        </div>,
      );
      continue;
    }
    if (/^\s*([-*]|\d+\.)\s+/.test(line)) {
      const ordered = /^\s*\d+\./.test(line);
      const items = [];
      while (i < lines.length && /^\s*([-*]|\d+\.)\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*([-*]|\d+\.)\s+/, ''));
        i += 1;
      }
      const List = ordered ? 'ol' : 'ul';
      out.push(
        <List className="list" key={`l${i}`}>
          {items.map((t, k) => <li key={k}>{inline(t, k)}</li>)}
        </List>,
      );
      continue;
    }
    if (line.startsWith('>')) {
      const quote = [];
      while (i < lines.length && lines[i].startsWith('>')) quote.push(lines[i++].replace(/^>\s?/, ''));
      out.push(<blockquote key={`q${i}`}>{inline(quote.join(' '), i)}</blockquote>);
      continue;
    }
    const para = [lines[i++]]; // always consume at least one line
    while (i < lines.length && lines[i].trim() && !/^(#{1,3}\s|\||>|\s*([-*]|\d+\.)\s)/.test(lines[i])) para.push(lines[i++]);
    out.push(<p key={`p${i}`}>{inline(para.join(' '), i)}</p>);
  }
  return <div className="md" dir="auto">{out}</div>;
}
