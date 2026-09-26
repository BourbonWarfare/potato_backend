from quart import render_template_string

from bw.web_utils import load_template_from_disk

NEGATIVE_OFFSET = 5
POSITIVE_OFFSET = 1
ERROR_START = -3


def _norm_path(p: str) -> str:
    return p.strip().strip('"').replace('/', '\\').lstrip('\\').lower()


def _locate_arma_error(content: str, source_file: str, error_position: int):
    """Map preprocessed text back to source lines via #line directives and find
    which source line/column the byte offset lands on."""
    target = _norm_path(source_file)
    source: dict[int, str] = {}
    cur, in_file = None, True  # no directives -> raw text is the file
    offset = 0
    hit_line = hit_col = None

    for raw in content.splitlines(keepends=True):
        size = len(raw.encode())
        text = raw.rstrip('\r\n')
        if text.startswith('#line '):
            num, _, fname = text[6:].partition(' ')
            try:
                cur = int(num)
                in_file = not target or _norm_path(fname) == target
            except ValueError:
                pass
        elif not text.startswith('#'):
            if cur is None:
                cur = 1
            if in_file:
                source[cur] = text
                if hit_line is None and offset <= error_position < offset + size:
                    hit_line, hit_col = cur, error_position - offset
            cur += 1
        offset += size

    lines = [source.get(i, '') for i in range(1, max(source, default=0) + 1)]
    return lines, hit_line, hit_col


async def format_arma_script_error(message: str) -> str:
    sections = message.split('+' * 5)
    if len(sections) != 5:
        return message

    error_text, source_file, line_number, error_position, content = sections
    source_file = source_file.strip()
    try:
        line_number = int(line_number)
        error_position = int(error_position)
    except ValueError:
        return message

    lines, hit_line, col = _locate_arma_error(content, source_file, error_position)
    if hit_line is not None:
        line_number = hit_line  # offset is authoritative; ARMA's line agrees in both examples
    else:
        col = 0

    location = source_file or 'Line/Pos'
    error_info = f'{location}:{line_number}:{col}'

    if lines:
        array_idx = min(max(0, line_number - 1), len(lines) - 1)
        start = max(0, array_idx - NEGATIVE_OFFSET)
        window = lines[start : array_idx + POSITIVE_OFFSET]
        rel = array_idx - start

        line_len = len(window[rel])
        caret_start = min(max(0, col + ERROR_START), line_len)
        window.insert(rel + 1, '~' * caret_start + '^' * max(1, line_len - caret_start))
        content_relevant = '\n'.join(window)
    else:
        content_relevant = 'No script found within event.'

    template = await load_template_from_disk(template_path='server_ops/arma/script_error.template.html')
    return await render_template_string(
        template,
        script_error=error_text.strip(),
        code_context=error_info,
        code=content_relevant,
    )


async def format_arma_event(tag: str, message: str) -> str:
    match tag:
        case 'script-error':
            return await format_arma_script_error(message)
        case _:
            return message
