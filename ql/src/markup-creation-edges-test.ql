import MarkupCreationTestUtils

from MarkupCreationCFG::Node a, MarkupCreationCFG::Node b
where MarkupCreationCFG::edge(a, b)
select file(a), scope(a), identity(a), identity(b)
