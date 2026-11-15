import { open } from 'fs';
{ let open = function(x) { return 'shadow'; }; printf('local=%s\n', open("fixtures/native.txt"));
}
