/**
 * @name setInitAction action token switch
 * @description M4: setInitAction.call switches on request.args.action string tokens. This is caller-side inventory, not a sanitizer of name or of luci.sys.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/m4/setinitaction-action-switch
 * @tags testing
 */

import codeql.ucode.m3.Models

from UCODE::SwitchStatement sw, UCODE::SwitchCase c, string label
where
  inSetInitActionCall(sw) and
  exists(RequestArgsAccess a |
    a.getProperty().getValue() = "action" and
    a.getParent*() = sw.getValue()
  ) and
  c.getParent*() = sw.getBody() and
  label = stringLiteralValue(c.getValue().(UCODE::String))
select c, "setInitAction action token '" + label + "' (not a sanitizer of name)"
