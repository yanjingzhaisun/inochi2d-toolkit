"""inochi2d-toolkit: read, verify and build Inochi2D puppets.

Public API (stable enough to build on):

    from inochi2d_toolkit import inp, build, puppet

    doc = inp.load("model.inx")
    issues = puppet.validate(doc)
    inp.save(doc, "model.out.inx")
"""

from . import build, cli, inp, puppet

__all__ = ["build", "cli", "inp", "puppet"]
__version__ = cli.__version__
