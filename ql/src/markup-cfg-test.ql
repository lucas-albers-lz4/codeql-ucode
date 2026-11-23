import codeql.ucode.MarkupCFG
import MarkupCfgTestUtils

from MarkupCFG::Node a, MarkupCFG::Node b
where MarkupCFG::edge(a, b)
select a.getScope().getLocation().getFile().getBaseName(), identity(a), identity(b),
  count(MarkupCFG::Node c, MarkupCFG::Node d |
    MarkupCFG::edge(c, d) and c.getScope() = a.getScope() and d.getScope() = b.getScope() and
    identity(c) = identity(a) and identity(d) = identity(b)
  )
