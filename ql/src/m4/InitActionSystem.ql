/**
 * @name luci.sys init_action builtin system
 * @description M4: extracted luci.sys init_action interpolates its parameters into builtin system. basename is not a modeled sanitizer.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/m4/init-action-system
 * @tags testing
 */

import codeql.ucode.m3.Models

string interpNote(BuiltinSystemCall c) {
  exists(UCODE::TemplateString tmpl | tmpl = c.getArgument(0)) and
  result = "template interpolates name/action (basename is not a modeled sanitizer)"
  or
  not exists(UCODE::TemplateString tmpl | tmpl = c.getArgument(0)) and
  result = "non-template argument"
}

from BuiltinSystemCall c
where inInitAction(c)
select c, "init_action calls builtin system; " + interpNote(c)
