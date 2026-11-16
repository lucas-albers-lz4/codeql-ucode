function ordinary(value) { return value; }
function gather(...xs) { return xs; }
function gather2(head, ...tail) { if (head) return tail; return tail; }
ordinary('plain');
gather();
gather('a');
gather('b', 'c');
gather2('prefix0');
gather2('prefix1', 'd');
gather2('prefix2', 'e', 'f');
