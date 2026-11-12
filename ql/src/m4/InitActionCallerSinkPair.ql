/**
 * @name setInitAction request.args paired with init_action system
 * @description M4: syntactic pair of a tainted init_action call in setInitAction with the extracted luci.sys system sink. Not interprocedural dataflow; not path_found.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/m4/init-action-caller-sink-pair
 * @tags testing
 */

import codeql.ucode.m3.Models

predicate initActionFromLuciSys(NamedCall c) {
  c.getName() = "init_action" and
  exists(UCODE::ImportStatement imp |
    imp.getLocation().getFile() = c.getLocation().getFile() and
    namedImport(imp, "luci.sys", "init_action")
  )
}

from RequestArgsAccess src, NamedCall c, BuiltinSystemCall sys
where
  src.getLocation().getFile().getBaseName() = "luci" and
  src.getProperty().getValue() != "args" and
  inSetInitActionCall(src) and
  initActionFromLuciSys(c) and
  taintReachesSink(src, c) and
  inInitAction(sys)
select src,
  "request.args reaches imported init_action; luci.sys body has builtin $@ (syntactic pair, not interprocedural dataflow)",
  sys, "system"
