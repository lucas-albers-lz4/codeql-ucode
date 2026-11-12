/**
 * @name request.args into imported callee
 * @description M4: request.args reaches a call whose callee is imported from another module. The callee body is not extracted in this slice (unresolved_call).
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/m4/imported-callee-taint
 * @tags testing
 */

import codeql.ucode.m3.Models

predicate importedFrom(NamedCall c, string moduleName) {
  exists(UCODE::ImportStatement imp |
    imp.getLocation().getFile() = c.getLocation().getFile() and
    namedImport(imp, moduleName, c.getName())
  ) and
  moduleName != "fs"
}

from RequestArgsAccess src, NamedCall c, string moduleName
where
  src.getLocation().getFile().getBaseName() = "luci" and
  src.getProperty().getValue() != "args" and
  taintReachesSink(src, c) and
  importedFrom(c, moduleName)
select src,
  c.getName() + " from '" + moduleName + "' takes request.args (callee body not extracted)", c,
  c.getName()
