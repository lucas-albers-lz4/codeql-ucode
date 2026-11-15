/** Scratch query mutant: suppress all genuine Models classifications. */
import codeql.ucode.m3.Models
from NamedFsPopenCall c
where none()
select c, "named fs popen in " + c.getLocation().getFile().getBaseName()
