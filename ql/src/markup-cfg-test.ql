import codeql.ucode.MarkupCFG
import MarkupCfgTestUtils

from MarkupCFG::Node a, MarkupCFG::Node b
where MarkupCFG::edge(a, b)
select a.getScope().getLocation().getFile().getBaseName(), identity(a), identity(b)
