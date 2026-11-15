import { readlink } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
let obj={ readlink }; probe('member', obj.readlink("probe-link"));
