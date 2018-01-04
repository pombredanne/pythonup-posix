import click

from pym import paths
from pym.conf import settings


def safe_link(source, target):
    if target.exists():
        if source.samefile(target):
            return False
        target.unlink()
    target.symlink_to(source)
    return True


def safe_unlink(target):
    if target.exists():
        target.unlink()


def link_commands(version):
    installation = version.find_installation()
    for target in version.python_commands:
        safe_link(installation.python, target)
    for target in version.pip_commands: # TODO: These should be shimmed.
        safe_link(installation.pip, target)


def unlink_commands(version):
    for target in version.python_commands:
        safe_unlink(target)
    for target in version.pip_commands:
        safe_unlink(target)


def collect_link_sources(versions):
    link_sources = {}
    shim_sources = {}
    for version in versions:
        installation = version.find_installation()
        blacklisted_stems = {
            # Encourage people to always use qualified commands.
            'python', 'easy_install', 'pip',
            # Fully qualified names are already populated on installation.
            'python{}'.format(version.name),
            'pip{}'.format(version.name),
        }
        shimmed_stems = {
            # Major version names, e.g. "pip3".
            'pip{}'.format(version.major),
            # Fully-qualified easy_install.
            'easy_install-{}'.format(version.name),
        }
        for path in installation.root.joinpath('bin').iterdir():
            if path.stem in blacklisted_stems:
                continue
            if path.stem in shimmed_stems:
                if path.name not in shim_sources:
                    shim_sources[path.name] = path
            else:
                if path.name not in link_sources:
                    link_sources[path.name] = path
    return link_sources, shim_sources


def use_versions(versions):
    link_sources, shim_sources = collect_link_sources(versions)
    bindir = paths.get_pym_bin()

    # TODO: Only show this if there really are things to link.
    # We will need to calculate samefiles for this to happen.
    if link_sources or shim_sources:
        click.echo('Publishing executables...')

    for name, source in link_sources.items():
        if safe_link(source, bindir.joinpath(name)):
            click.echo(f'  {name}')
    for name, source in shim_sources.items():   # TODO: Shimm these instead.
        if safe_link(source, bindir.joinpath(name)):
            click.echo(f'  {name}')

    settings['using'] = [v.name for v in versions]

    stale_targets = set(
        path for path in bindir.iterdir()
        if path.name not in link_sources and path.name not in shim_sources
    )
    if stale_targets:
        click.echo('Cleaning stale executables...')
    for path in stale_targets:
        safe_unlink(path)
        click.echo(f'  {path.name}')
