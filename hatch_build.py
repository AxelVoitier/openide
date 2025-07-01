# This trampoline script (instead of directly defining openide/integrations/hatch_hook.py
# as the path for hatch custom build hook is solely because while it works well when doing
# `hatch build wheel`, it fails when doing `pip install .` (or editable variant),
# because it cannot the script tries to import various things from openide, and when
# doing that with pip it fails to resolve it.
# It seems just adding the local folder onto the python path does the trick.

import sys

sys.path.insert(0, '.')

from openide.integrations.hatch_hook import OpenIDEYAMLBuildHook
