function probe(label, value) { printf('%s=%s\n', label, value); }
let popen = function(x) { return 'shadow'; }; probe('absent', popen("probe-link"));
