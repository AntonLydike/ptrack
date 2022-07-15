import time

from .watch import PackageWatcher
import click

file_arg = click.argument(
    "file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True, writable=False)
)


@click.group('ptrack')
def ptrack():
    pass


@ptrack.command('i3bar')
@file_arg
def i3_display(file: str):
    task = PackageWatcher(file, 'i3bar')
    while True:
        print(task.tick())
        time.sleep(1)


@ptrack.command('view')
@file_arg
@click.option('-m', '--viewmode', help="in what format to display the info", default="compact")
@click.option('-n', '--refresh', help="the rate at which to refresh", default=1)
def view(file: str, viewmode: str, refresh: int):
    task = PackageWatcher(file, viewmode)
    while True:
        task.tick()
        time.sleep(int(refresh))


if __name__ == '__main__':
    ptrack()
