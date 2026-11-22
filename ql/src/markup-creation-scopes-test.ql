import codeql.ucode.MarkupCreationCFG

string status(MarkupCreationCFG::CallableScope f) {
  MarkupCreationCFG::isCallableCovered(f) and result = "covered"
  or
  not MarkupCreationCFG::isCallableCovered(f) and result = "unsupported"
}

from MarkupCreationCFG::CallableScope f
select f.getLocation().getFile().getBaseName(), f.getLocation().getStartLine(),
  f.getLocation().getStartColumn(), f.getLocation().getEndLine(), f.getLocation().getEndColumn(),
  status(f)
