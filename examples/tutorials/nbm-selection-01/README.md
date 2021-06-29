# nbm-selection-01 tutorial

This is a reimplementation of [Netbeans Platform selection tutorial, part 1](https://netbeans.apache.org/tutorials/nbm-selection-1.html). But using Python OpenIDE framework.

Install it first in an environment:
```
$ pip install .
```

Then run it with:
```
$ nbm-selection-01
```

It is essential to install it first (with `pip` or `python3 setup.py install`) as the package building process is generating an important Egg-info file used by OpenIDE framework to discover what to instantiate from this package.
