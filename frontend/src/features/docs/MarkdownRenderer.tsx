import type { ReactElement } from 'react';
import { Link } from 'react-router-dom';
import { CodeBlockWithCopy } from './CodeBlockWithCopy';
import { DocsChecklist } from './DocsChecklist';
import { DocsCommonMistakes } from './DocsCommonMistakes';
import { DocsConceptCallout } from './DocsConceptCallout';
import { DocsExpectedResult } from './DocsExpectedResult';
import { DocsLessonPage } from './DocsLessonPage';
import { DocsNextLesson } from './DocsNextLesson';
import { ExampleBlock } from './ExampleBlock';
import { OpenPageLink } from './OpenPageLink';
import { Screenshot } from './Screenshot';
import { ScreenshotPlaceholder } from './ScreenshotPlaceholder';
import type { TocItem } from './types';

function slugify(value: string) {
  return value.toLowerCase().trim().replace(/[^\p{L}\p{N}\s-]/gu, '').replace(/\s+/g, '-').replace(/-+/g, '-');
}

const utilityTocHeadings = new Set(['следующий урок', 'next lesson', '下一课']);

export function extractToc(markdown: string): TocItem[] {
  return markdown.split('\n').flatMap((line) => {
    const match = /^(#{2,3})\s+(.+)$/.exec(line.trim());
    if (!match) return [];
    const text = stripInline(match[2]);
    if (utilityTocHeadings.has(text.toLowerCase().trim())) return [];
    return [{ id: slugify(match[2]), text, level: match[1].length }];
  });
}

export function MarkdownRenderer({ markdown }: { markdown: string }) {
  const nodes = parseMarkdown(markdown);
  return <article className="docs-markdown">{nodes}</article>;
}

function parseMarkdown(markdown: string) {
  const lines = markdown.split('\n');
  const nodes: ReactElement[] = [];
  let paragraph: string[] = [];
  let list: string[] = [];
  let orderedList: string[] = [];
  let table: string[] = [];
  let code: string[] | null = null;
  let codeLanguage = 'text';

  function flushParagraph() {
    if (!paragraph.length) return;
    nodes.push(<p key={`p-${nodes.length}`}>{renderInline(paragraph.join(' '))}</p>);
    paragraph = [];
  }
  function flushList() {
    if (!list.length) return;
    nodes.push(<ul key={`ul-${nodes.length}`}>{list.map((item, index) => <li key={index}>{renderInline(item)}</li>)}</ul>);
    list = [];
  }
  function flushOrderedList() {
    if (!orderedList.length) return;
    nodes.push(<ol key={`ol-${nodes.length}`}>{orderedList.map((item, index) => <li key={index}>{renderInline(item)}</li>)}</ol>);
    orderedList = [];
  }
  function flushTable() {
    if (table.length < 2) { table = []; return; }
    const rows = table.map((line) => line.split('|').map((cell) => cell.trim()).filter(Boolean));
    const [head, , ...body] = rows;
    nodes.push(<table key={`tbl-${nodes.length}`}><thead><tr>{head.map((cell) => <th key={cell}>{renderInline(cell)}</th>)}</tr></thead><tbody>{body.map((row, rowIndex) => <tr key={rowIndex}>{row.map((cell, cellIndex) => <td key={cellIndex}>{renderInline(cell)}</td>)}</tr>)}</tbody></table>);
    table = [];
  }
  function flushAll() { flushParagraph(); flushList(); flushOrderedList(); flushTable(); }

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();
    const fence = /^(?:```|~~~)(\w+|1c)?\s*$/.exec(line.trim());
    if (fence) {
      if (code !== null) {
        nodes.push(<CodeBlockWithCopy key={`code-${nodes.length}`} language={codeLanguage} code={code.join('\n')} />);
        code = null;
        codeLanguage = 'text';
      } else {
        flushAll();
        code = [];
        codeLanguage = fence[1] || 'text';
      }
      continue;
    }
    if (code !== null) { code.push(rawLine); continue; }

    const screenshotShortcode = /^::screenshot\{(.+)\}$/.exec(line.trim());
    if (screenshotShortcode) {
      flushAll();
      const attrs = parseShortcodeAttrs(screenshotShortcode[1]);
      nodes.push(<Screenshot key={`shot-${nodes.length}`} assetId={attrs.assetId ?? attrs.id ?? ''} label={attrs.label} />);
      continue;
    }
    const exampleShortcode = /^::example\{(.+)\}$/.exec(line.trim());
    if (exampleShortcode) {
      flushAll();
      const attrs = parseShortcodeAttrs(exampleShortcode[1]);
      nodes.push(<ExampleBlock key={`example-${nodes.length}`} exampleId={attrs.exampleId ?? attrs.id ?? ''} />);
      continue;
    }
    const openPageShortcode = /^::open-page\{(.+)\}$/.exec(line.trim());
    if (openPageShortcode) {
      flushAll();
      const attrs = parseShortcodeAttrs(openPageShortcode[1]);
      nodes.push(<OpenPageLink key={`open-${nodes.length}`} route={attrs.route ?? '/'} label={attrs.label ?? attrs.route ?? 'Open page'} />);
      continue;
    }
    const checklistShortcode = /^::checklist\{(.+)\}$/.exec(line.trim());
    if (checklistShortcode) {
      flushAll();
      const attrs = parseShortcodeAttrs(checklistShortcode[1]);
      const items = (attrs.items ?? '').split('|').map((item) => item.trim()).filter(Boolean);
      nodes.push(<DocsChecklist key={`checklist-${nodes.length}`} id={attrs.id ?? `checklist-${nodes.length}`} items={items} />);
      continue;
    }
    const lessonPageShortcode = /^::lesson-page\{(.+)\}$/.exec(line.trim());
    if (lessonPageShortcode) {
      flushAll();
      const attrs = parseShortcodeAttrs(lessonPageShortcode[1]);
      nodes.push(<DocsLessonPage key={`lesson-${nodes.length}`} label={attrs.label} />);
      continue;
    }
    const conceptCalloutShortcode = /^::concept-callout\{(.+)\}$/.exec(line.trim());
    if (conceptCalloutShortcode) {
      flushAll();
      const attrs = parseShortcodeAttrs(conceptCalloutShortcode[1]);
      nodes.push(<DocsConceptCallout key={`concept-${nodes.length}`} title={attrs.title ?? 'Concept'} body={decodeAttr(attrs.body ?? '')} />);
      continue;
    }
    const expectedResultShortcode = /^::expected-result\{(.+)\}$/.exec(line.trim());
    if (expectedResultShortcode) {
      flushAll();
      const attrs = parseShortcodeAttrs(expectedResultShortcode[1]);
      const items = (attrs.items ?? '').split('|').map((item) => item.trim()).filter(Boolean);
      nodes.push(<DocsExpectedResult key={`expected-${nodes.length}`} items={items} />);
      continue;
    }
    const commonMistakesShortcode = /^::common-mistakes\{(.+)\}$/.exec(line.trim());
    if (commonMistakesShortcode) {
      flushAll();
      const attrs = parseShortcodeAttrs(commonMistakesShortcode[1]);
      const items = (attrs.items ?? '').split('|').map((item) => item.trim()).filter(Boolean);
      nodes.push(<DocsCommonMistakes key={`mistakes-${nodes.length}`} items={items} />);
      continue;
    }
    const nextLessonShortcode = /^::next-lesson\{(.+)\}$/.exec(line.trim());
    if (nextLessonShortcode) {
      flushAll();
      const attrs = parseShortcodeAttrs(nextLessonShortcode[1]);
      nodes.push(<DocsNextLesson key={`next-${nodes.length}`} label={attrs.label} href={attrs.href} />);
      continue;
    }

    const screenshot = /^\{\{screenshot:(.+)\}\}$/.exec(line.trim());
    if (screenshot) { flushAll(); nodes.push(<ScreenshotPlaceholder key={`shot-${nodes.length}`} label={screenshot[1].trim()} />); continue; }
    const bracketScreenshot = /^\[SCREENSHOT:\s*(.+)\]$/.exec(line.trim());
    if (bracketScreenshot) { flushAll(); nodes.push(<ScreenshotPlaceholder key={`shot-${nodes.length}`} label={bracketScreenshot[1].trim()} />); continue; }

    if (!line.trim()) { flushAll(); continue; }
    if (line.startsWith('|')) { flushParagraph(); flushList(); flushOrderedList(); table.push(line); continue; }
    const heading = /^(#{1,4})\s+(.+)$/.exec(line.trim());
    if (heading) {
      flushAll();
      const level = heading[1].length;
      const text = stripInline(heading[2]);
      const id = slugify(text);
      if (level === 1) nodes.push(<h1 id={id} key={`h-${nodes.length}`}>{renderInline(heading[2])}</h1>);
      else if (level === 2) nodes.push(<h2 id={id} key={`h-${nodes.length}`}>{renderInline(heading[2])}</h2>);
      else if (level === 3) nodes.push(<h3 id={id} key={`h-${nodes.length}`}>{renderInline(heading[2])}</h3>);
      else nodes.push(<h4 id={id} key={`h-${nodes.length}`}>{renderInline(heading[2])}</h4>);
      continue;
    }
    const quote = /^>\s+(.+)$/.exec(line.trim());
    if (quote) { flushAll(); nodes.push(<blockquote key={`q-${nodes.length}`}>{renderInline(quote[1])}</blockquote>); continue; }
    const bullet = /^[-*]\s+(.+)$/.exec(line.trim());
    if (bullet) { flushParagraph(); flushOrderedList(); flushTable(); list.push(bullet[1]); continue; }
    const ordered = /^\d+\.\s+(.+)$/.exec(line.trim());
    if (ordered) { flushParagraph(); flushList(); flushTable(); orderedList.push(ordered[1]); continue; }
    flushList();
    flushOrderedList();
    flushTable();
    paragraph.push(line.trim());
  }
  if (code !== null) nodes.push(<CodeBlockWithCopy key={`code-${nodes.length}`} language={codeLanguage} code={code.join('\n')} />);
  flushAll();
  return nodes;
}

function stripInline(value: string) {
  return value.replace(/\[([^\]]+)\]\([^)]+\)/g, '$1').replace(/[`*_]/g, '');
}

function renderInline(value: string) {
  const parts = value.split(/(\[[^\]]+\]\([^)]+\)|`[^`]+`|\*\*[^*]+\*\*)/g).filter(Boolean);
  return parts.map((part, index) => {
    const link = /^\[([^\]]+)\]\(([^)]+)\)$/.exec(part);
    if (link) {
      const href = link[2];
      const external = /^https?:\/\//.test(href);
      if (href.startsWith('/')) return <Link key={index} to={href}>{link[1]}</Link>;
      return <a key={index} href={href} target={external ? '_blank' : undefined} rel={external ? 'noreferrer' : undefined}>{link[1]}</a>;
    }
    if (part.startsWith('`') && part.endsWith('`')) return <code key={index}>{part.slice(1, -1)}</code>;
    if (part.startsWith('**') && part.endsWith('**')) return <strong key={index}>{part.slice(2, -2)}</strong>;
    return <span key={index}>{part}</span>;
  });
}

function parseShortcodeAttrs(value: string) {
  const attrs: Record<string, string> = {};
  for (const match of value.matchAll(/(\w+)="([^"]*)"/g)) attrs[match[1]] = match[2];
  return attrs;
}

function decodeAttr(value: string) {
  return value.replace(/&quot;/g, '"');
}
