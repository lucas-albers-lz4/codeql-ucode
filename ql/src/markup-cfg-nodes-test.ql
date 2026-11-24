import MarkupCfgTestUtils

from MarkupCFG::Node n
select n.getScope().getLocation().getFile().getBaseName(), n.getRole(), identity(n),
  count(MarkupCFG::Node duplicate |
    duplicate.getScope() = n.getScope() and duplicate.getRole() = n.getRole() and
    identity(duplicate) = identity(n)
  )
