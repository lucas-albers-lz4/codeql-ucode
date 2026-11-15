import { popen } from 'fs';
{ let popen = function(x) { return 'shadow'; }; print(popen('unused'), '\n'); }
