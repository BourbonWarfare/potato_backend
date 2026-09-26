import nh3
from quart import render_template_string

from bw.web_utils import load_template_from_disk


async def format_arma_script_error(message: str) -> str:
    NEGATIVE_OFFSET = 5
    POSITIVE_OFFSET = 1
    ERROR_START = -3

    sections = message.split('+' * 5)
    if len(sections) != 5:
        return message

    error_text, source_file, line_number, error_position, raw = (s.strip('\r\n') for s in sections)
    source_file = source_file.strip()
    try:
        line_number = int(line_number)
        error_position = int(error_position)
    except ValueError:
        return message
    content = raw.splitlines()

    if content and content[0].startswith('#'):
        source_line_number = 0
        error_position -= len(content.pop(0).encode()) + 1
        while content and (not content[0].strip() or content[0].startswith('#')):
            to_ignore = content.pop(0)
            error_position -= len(to_ignore.encode()) + 1
            if source_file and to_ignore.startswith('#line ') and source_file in to_ignore:
                try:
                    source_line_number = int(to_ignore.removeprefix('#line ').split(' ')[0])
                except ValueError:
                    pass
        content = [''] * source_line_number + content  # verify: maybe source_line_number - 1

    error_info = f'{source_file}:{line_number}:{error_position}' if source_file else f'Line/Pos:{line_number}:{error_position}'

    if content:
        # line number - 2 because:
        # line number starts at 1, not 0 (-1)
        # we want to remove the positions before the target line (-1)
        error_position -= sum([1 + len(s.encode()) for s in content[: max(0, line_number - 2)]])
        error_info = (
            f'{source_file}:{line_number}:{error_position}' if source_file else f'Line/Pos:{line_number}:{error_position}'
        )

        array_idx = min(max(0, line_number - 1), len(content) - 1)
        error_start = max(0, array_idx - NEGATIVE_OFFSET)
        content_relevant = content[error_start : array_idx + POSITIVE_OFFSET]

        rel = array_idx - error_start
        error_line_length = len(content_relevant[rel])
        error_line_start = min(max(0, error_position + ERROR_START), error_line_length)
        content_relevant.insert(rel + 1, '~' * error_line_start + '^' * (error_line_length - error_line_start))
        content_relevant = '\n'.join(content_relevant)
    else:
        content_relevant = 'No script found within event.'

    template = await load_template_from_disk(template_path='server_ops/arma/script_error.template.html')
    return await render_template_string(
        template,
        script_error=nh3.clean(error_text),
        code_context=nh3.clean(error_info),
        code=nh3.clean(content_relevant),
    )


async def format_arma_event(tag: str, message: str) -> str:
    match tag:
        case 'script-error':
            return await format_arma_script_error(message)
        case _:
            return message
