"""MCP tool registration for Serbian Data MCP Server.

Each domain module registers its tools on the shared FastMCP instance.
Importing this package triggers all registrations.
"""

from . import search  # noqa: F401
from . import data  # noqa: F401
from . import transform  # noqa: F401
from . import visualization  # noqa: F401
from . import analysis  # noqa: F401
from . import maps  # noqa: F401
from . import export  # noqa: F401
from . import resources  # noqa: F401
from . import prompts  # noqa: F401
from . import novel_charts  # noqa: F401
from . import animations  # noqa: F401
