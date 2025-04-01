import sys

colors_table = {
    'BLACK':   [ '30', '40' ],
    'RED':     [ '31', '41' ],
    'GREEN':   [ '32', '42' ],
    'YELLOW':  [ '33', '43' ],
    'BLUE':    [ '34', '44' ],
    'MAGENTA': [ '35', '45' ],
    'CYAN':    [ '36', '46' ],
    'WHITE':   [ '37', '47' ],
    'DEFAULT': [ '39', '49' ],
    'RESET':   [ '00', '00' ],
}

def set_color(fg: str = 'DEFAULT', bg: str = 'DEFAULT', file=sys.stdout):
    bg = bg.upper()
    fg = fg.upper()
    if bg not in colors_table:
        raise ValueError(f'{bg} is not a valid color!, we only support 8 colors only!')
    if fg not in colors_table:
        raise ValueError(f'{fg} is not a valid color!, we only support 8 colors only!')
    print(f"\033[{colors_table[fg][0]};{colors_table[bg][1]}m", file=file, end='')


def printf(fg: str, bg: str, msg: str, file=sys.stdout, *args, **kwargs):
    set_color(fg, bg, file)
    print(msg, file=file, **kwargs)
    set_color(file=file)
