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

    error_text, source_file, line_number, error_position, content = sections
    error_text = nh3.clean(error_text)
    source_file = nh3.clean(source_file)
    line_number = int(line_number)
    content = nh3.clean(content).splitlines()
    while content and (not content[0] or content[0].isspace() or content[0][0] == '#'):
        content.pop(0)

    if content:
        error_position = int(error_position) - sum([len(s.encode()) for s in content[:line_number]])

        if source_file:
            error_info = f'{source_file}:{line_number}:{error_position}'
        else:
            error_info = f'Line/Pos:{line_number}:{error_position}'

        array_idx = max(0, line_number - 1)
        error_start = max(0, array_idx - NEGATIVE_OFFSET)
        content_relevant = content[error_start : array_idx + POSITIVE_OFFSET]

        relative_line_number = min(len(content_relevant) - 1, NEGATIVE_OFFSET - 1)
        error_line_length = len(content_relevant[relative_line_number])
        error_line_start = max(0, error_position + ERROR_START)
        error_line_context_length = error_line_length - error_line_start
        content_relevant.insert(relative_line_number, '-' * error_line_start + '^' * error_line_context_length)
        content_relevant = '\n'.join(content_relevant)
    else:
        content_relevant = 'No script found within event.'

    template = await load_template_from_disk(template_path='server_ops/arma/script_error.template.html')
    return await render_template_string(template, script_error=error_text, code_context=error_info, code=content_relevant)


async def format_arma_event(tag: str, message: str) -> str:
    match tag:
        case 'script-error':
            return await format_arma_script_error(message)
        case _:
            return message
