function template_controls(first, second, third) {
	const plain = popen("plain argument");
	const literalOnly = popen(`literal only`);
	const one = popen(`prefix ${shellquote(first)} suffix`);
	const multiple = system(`before ${shellquote(first)} middle ${shellquote(second + nested(third))} after`);
	const indexed = system("ordinary", `index ${nested(first)}`, "tail");
	return [plain, one, multiple, indexed];
}
