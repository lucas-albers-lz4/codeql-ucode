/**
 * @name Syntactic ubus.call inventory
 * @description Identifies direct ubus.call member call sites; the receiver binding and runtime behavior are not resolved. Inventory only.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/m4/ubus-call-inventory
 * @tags testing
 */

import codeql.ucode.Concepts
import codeql.files.FileSystem

from UbusCall c
select c, "ubus_call fact in " + c.getLocation().getFile().getBaseName() + " at line " +
  c.getLocation().getStartLine().toString()
