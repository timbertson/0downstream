
let () =
	let nv = match Sys.argv with
		| [|_;name; ver|] -> OpamPackage.create (OpamPackage.Name.of_string name) (OpamPackage.Version.of_string ver)
		| _ -> failwith "Invalid args"
	in
	let t = OpamState.load_state "install_only" in
	OpamAction.build_and_install_package ~metadata:false t nv
