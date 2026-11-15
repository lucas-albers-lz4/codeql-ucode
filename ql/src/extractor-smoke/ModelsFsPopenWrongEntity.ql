/** Scratch query mutant: same genuine row labels/count, wrong entity URL. */
import codeql.ucode.m3.Models
from NamedFsPopenCall c
select c.getFunction(), "named fs popen in " + c.getLocation().getFile().getBaseName()
