module URL = OpamFile.URL
module OPAM = OpamFile.OPAM
module Descr = OpamFile.Descr
open OpamTypes

let maybe_string s = match s with
	| Some s -> `String s
	| None -> `Null

let dump_json data =
	let json_str = OpamJson.to_string data in
	print_endline json_str

let json_of_os_constr cons : OpamJson.t =
	let (bool, str) = cons in
	`A [
		`Bool bool;
		`String str;
	]

let json_of_compiler_version_constraint cons : OpamJson.t =
	let (relop, ver) = cons in
	`A [
		`String (OpamFormula.string_of_relop relop);
		OpamCompiler.Version.to_json ver
	]

let json_of_version_constraint (cons:OpamFormula.version_constraint) : OpamJson.t =
	let (relop, ver) = cons in
	`A [
		`String (OpamFormula.string_of_relop relop);
		OpamPackage.Version.to_json ver
	]

type dep = (OpamPackage.Name.t * OpamFormula.version_formula)
let rec json_of_dependency (dep:dep) : OpamJson.t =
	let (name, version) = dep in
	`O [
		("name", OpamPackage.Name.to_json name);
		("constraints", json_of_formula json_of_version_constraint version);
	]

and json_of_formula : 'a . ('a -> OpamJson.t) -> 'a OpamFormula.formula -> OpamJson.t =
	fun atom_to_json formula ->
	let recurse = json_of_formula atom_to_json in
	let open OpamFormula in
	match formula with
		| Empty -> `Null
		| Atom f -> atom_to_json f
		| Block f -> recurse f
		| And (a,b) -> `A [`String "&&"; (recurse a); (recurse b)]
		| Or (a,b) -> `A [`String "||"; (recurse a); (recurse b)]

let json_of_depends : dep OpamFormula.formula -> OpamJson.t =
	json_of_formula json_of_dependency

let info_opam ic =
	let file = OPAM.read_from_channel ic in
	`O [
		("type", `String "opam");
		("ocaml_version", match (OPAM.ocaml_version file) with
			| None -> `Null
			| Some constr -> json_of_formula json_of_compiler_version_constraint constr
		);
		("os", json_of_formula json_of_os_constr (OPAM.os file));
		("depends", json_of_depends (OPAM.depends file));
		("depends_optional", json_of_depends (OPAM.depopts file));
		("depends_external", match OPAM.depexts file with
			| None -> `Null
			| Some deps ->
				OpamMisc.StringSetMap.to_json OpamMisc.StringSet.to_json deps;
		);
		("conflicts", json_of_depends (OPAM.conflicts file));
	]

let info_descr ic =
	let file = Descr.read_from_channel ic in
	`O [
		("type", `String "descr");
		("summary", `String (Descr.synopsis file));
		("description", `String (Descr.body file));
	]

let info_url ic =
	let file = URL.read_from_channel ic in
	`O [
		("type", `String "url");
		("url", `String (string_of_address (URL.url file)));
		("kind", maybe_string (Option.map string_of_repository_kind (URL.kind file)));
		("checksum", maybe_string (URL.checksum file));
	]

let () =
	let usage = "opam-to-json --type TYPE [file]" in

	let filetype = ref "" in
	let spec = Arg.align [
		("--type", Arg.Set_string filetype, " Set filetype (url|opam)");
	] in
	let args = ref [] in
	let add_arg x = args := x :: !args in
	Arg.parse spec add_arg usage;
	let usage_error () = failwith usage in
	let ic = match !args with
		| [] -> stdin
		| [f] -> open_in f
		| _ -> usage_error ()
	in
	let data = (match !filetype with
		| "url" -> info_url
		| "opam" -> info_opam
		| "descr" -> info_descr
		| _ -> usage_error ()
	) ic in
	dump_json data
