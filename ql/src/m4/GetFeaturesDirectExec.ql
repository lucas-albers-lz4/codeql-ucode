/**
 * @name getFeatures direct popen/system
 * @description M4: named fs popen and builtin system inside getFeatures.call itself (not the netifd helper).
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/m4/getfeatures-direct-exec
 * @tags testing
 */

import codeql.ucode.m3.Models

from NamedCall c, string kind
where
  inGetFeaturesCall(c) and
  (
    c instanceof NamedFsPopenCall and kind = "popen"
    or
    c instanceof BuiltinSystemCall and kind = "system"
  )
select c, "getFeatures.call " + kind + " at line " + c.getLocation().getStartLine().toString(), c,
  kind
