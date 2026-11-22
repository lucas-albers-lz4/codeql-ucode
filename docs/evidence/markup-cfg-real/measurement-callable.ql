import codeql.ucode.MarkupCreationCFG
from MarkupCreationCFG::CallableScope f, string coverage
where (MarkupCreationCFG::isCallableCovered(f) and coverage = "covered" or not MarkupCreationCFG::isCallableCovered(f) and coverage = "unsupported")
select f.getLocation().getFile().getRelativePath(), f.getLocation().getStartLine(), f.getLocation().getStartColumn(), f.getLocation().getEndLine(), f.getLocation().getEndColumn(), coverage
