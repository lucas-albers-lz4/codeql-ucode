import MarkupCfgTestUtils

from MarkupCFG::Node n
select n.getScope().getLocation().getFile().getBaseName(), n.getRole(), identity(n)
