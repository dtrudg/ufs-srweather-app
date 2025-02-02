#!/usr/bin/env python3

import unittest
import os
import sys
import argparse
import re
import glob

from python_utils import (
    import_vars,
    print_input_args,
    print_info_msg,
    print_err_msg_exit,
    create_symlink_to_file,
    define_macos_utilities,
    check_var_valid_value,
    flatten_dict,
    cd_vrfy,
    mkdir_vrfy,
    find_pattern_in_str,
    load_shell_config,
)


def link_fix(
    verbose,
    file_group,
    source_dir,
    target_dir,
    ccpp_phys_suite,
    constants,
    dot_or_uscore,
    nhw,
    run_task,
    sfc_climo_fields,
    **kwargs,
):
    """This file defines a function that links fix files to the target
    directory for a given SRW experiment. Only links files for one group
    at a time.

    Args:
        cfg_d: dictionary of settings
        file_group: could be on of ["grid", "orog", "sfc_climo"]
        source_dir: the path to directory where the file_group fix files
                    are linked from
        target_dir: the directory where the fix files should be linked to
        dot_or_uscore: str containing either a dot or an underscore
        nhw: grid parameter setting
        constants: dict containing the constants used by SRW
        run_task: boolean value indicating whether the task is to be run
                  in the experiment
        climo_fields: list of fields needed for climo

    Returns:
        a string: resolution
    """

    print_input_args(locals())

    valid_vals_file_group = ["grid", "orog", "sfc_climo"]
    check_var_valid_value(file_group, valid_vals_file_group)

    # Decompress the constants needed below.
    nh0 = constants["NH0"]
    nh3 = constants["NH3"]
    nh4 = constants["NH4"]
    tile_rgnl = constants["TILE_RGNL"]

    #
    # -----------------------------------------------------------------------
    #
    # Create symlinks in the target_dir pointing to the fix files.
    # These symlinks are needed by the make_orog, make_sfc_climo,
    # make_ic, make_lbc, and/or run_fcst tasks.
    #
    # Note that we check that each target file exists before attempting to
    # create symlinks.  This is because the "ln" command will create sym-
    # links to non-existent targets without returning with a nonzero exit
    # code.
    #
    # -----------------------------------------------------------------------
    #
    print_info_msg(
        f"Creating links in the {target_dir} directory to the grid files...",
        verbose=verbose,
    )
    #
    # -----------------------------------------------------------------------
    #
    # Create globbing patterns for grid, orography, and surface climatology
    # files.
    #
    #
    # For grid files (i.e. file_group set to "grid"), symlinks are created
    # in the FIXlam directory to files (of the same names) in the GRID_DIR.
    # These symlinks/files and the reason each is needed is listed below:
    #
    # 1) "C*.mosaic.halo${NHW}.nc"
    #    This mosaic file for the wide-halo grid (i.e. the grid with a ${NHW}-
    #    cell-wide halo) is needed as an input to the orography filtering
    #    executable in the orography generation task.  The filtering code
    #    extracts from this mosaic file the name of the file containing the
    #    grid on which it will generate filtered topography.  Note that the
    #    orography generation and filtering are both performed on the wide-
    #    halo grid.  The filtered orography file on the wide-halo grid is then
    #    shaved down to obtain the filtered orography files with ${NH3}- and
    #    ${NH4}-cell-wide halos.
    #
    #    The raw orography generation step in the make_orog task requires the
    #    following symlinks/files:
    #
    #    a) C*.mosaic.halo${NHW}.nc
    #       The script for the make_orog task extracts the name of the grid
    #       file from this mosaic file; this name should be
    #       "C*.grid.tile${TILE_RGNL}.halo${NHW}.nc".
    #
    #    b) C*.grid.tile${TILE_RGNL}.halo${NHW}.nc
    #       This is the
    #       The script for the make_orog task passes the name of the grid
    #       file (extracted above from the mosaic file) to the orography
    #       generation executable.  The executable then
    #       reads in this grid file and generates a raw orography
    #       file on the grid.  The raw orography file is initially renamed "out.oro.nc",
    #       but for clarity, it is then renamed "C*.raw_orog.tile${TILE_RGNL}.halo${NHW}.nc".
    #
    #    c) The fixed files thirty.second.antarctic.new.bin, landcover30.fixed,
    #       and gmted2010.30sec.int.
    #
    #    The orography filtering step in the make_orog task requires the
    #    following symlinks/files:
    #
    #    a) C*.mosaic.halo${NHW}.nc
    #       This is the mosaic file for the wide-halo grid.  The orography
    #       filtering executable extracts from this file the name of the grid
    #       file containing the wide-halo grid (which should be
    #       "${CRES}.grid.tile${TILE_RGNL}.halo${NHW}.nc").  The executable then
    #       looks for this grid file IN THE DIRECTORY IN WHICH IT IS RUNNING.
    #       Thus, before running the executable, the script creates a symlink in this run directory that
    #       points to the location of the actual wide-halo grid file.
    #
    #    b) C*.raw_orog.tile${TILE_RGNL}.halo${NHW}.nc
    #       This is the raw orography file on the wide-halo grid.  The script
    #       for the make_orog task copies this file to a new file named
    #       "C*.filtered_orog.tile${TILE_RGNL}.halo${NHW}.nc" that will be
    #       used as input to the orography filtering executable.  The executable
    #       will then overwrite the contents of this file with the filtered orography.
    #       Thus, the output of the orography filtering executable will be
    #       the file C*.filtered_orog.tile${TILE_RGNL}.halo${NHW}.nc.
    #
    #    The shaving step in the make_orog task requires the following:
    #
    #    a) C*.filtered_orog.tile${TILE_RGNL}.halo${NHW}.nc
    #       This is the filtered orography file on the wide-halo grid.
    #       This gets shaved down to two different files:
    #
    #        i) ${CRES}.oro_data.tile${TILE_RGNL}.halo${NH0}.nc
    #           This is the filtered orography file on the halo-0 grid.
    #
    #       ii) ${CRES}.oro_data.tile${TILE_RGNL}.halo${NH4}.nc
    #           This is the filtered orography file on the halo-4 grid.
    #
    #       Note that the file names of the shaved files differ from that of
    #       the initial unshaved file on the wide-halo grid in that the field
    #       after ${CRES} is now "oro_data" (not "filtered_orog") to comply
    #       with the naming convention used more generally.
    #
    # 2) "C*.mosaic.halo${NH4}.nc"
    #    This mosaic file for the grid with a 4-cell-wide halo is needed as
    #    an input to the surface climatology generation executable.  The
    #    surface climatology generation code reads from this file the number
    #    of tiles (which should be 1 for a regional grid) and the tile names.
    #    More importantly, using the ESMF function ESMF_GridCreateMosaic(),
    #    it creates a data object of type esmf_grid; the grid information
    #    in this object is obtained from the grid file specified in the mosaic
    #    file, which should be "C*.grid.tile${TILE_RGNL}.halo${NH4}.nc".  The
    #    dimensions specified in this grid file must match the ones specified
    #    in the (filtered) orography file "C*.oro_data.tile${TILE_RGNL}.halo${NH4}.nc"
    #    that is also an input to the surface climatology generation executable.
    #    If they do not, then the executable will crash with an ESMF library
    #    error (something like "Arguments are incompatible").
    #
    #    Thus, for the make_sfc_climo task, the following symlinks/files must
    #    exist:
    #    a) "C*.mosaic.halo${NH4}.nc"
    #    b) "C*.grid.tile${TILE_RGNL}.halo${NH4}.nc"
    #    c) "C*.oro_data.tile${TILE_RGNL}.halo${NH4}.nc"
    #
    # 3)
    #
    #
    # -----------------------------------------------------------------------
    #
    #
    if file_group == "grid":
        fns = [
            f"C*{dot_or_uscore}mosaic.halo{nhw}.nc",
            f"C*{dot_or_uscore}mosaic.halo{nh4}.nc",
            f"C*{dot_or_uscore}mosaic.halo{nh3}.nc",
            f"C*{dot_or_uscore}grid.tile{tile_rgnl}.halo{nhw}.nc",
            f"C*{dot_or_uscore}grid.tile{tile_rgnl}.halo{nh3}.nc",
            f"C*{dot_or_uscore}grid.tile{tile_rgnl}.halo{nh4}.nc",
        ]

    elif file_group == "orog":
        fns = [
            f"C*{dot_or_uscore}oro_data.tile{tile_rgnl}.halo{nh0}.nc",
            f"C*{dot_or_uscore}oro_data.tile{tile_rgnl}.halo{nh4}.nc",
        ]
        if ccpp_phys_suite == "FV3_HRRR" or ccpp_phys_suite == "FV3_GFS_v17_p8":
            fns += [
                f"C*{dot_or_uscore}oro_data_ss.tile{tile_rgnl}.halo{nh0}.nc",
                f"C*{dot_or_uscore}oro_data_ls.tile{tile_rgnl}.halo{nh0}.nc",
            ]

    #
    # The following list of symlinks (which have the same names as their
    # target files) need to be created for the make_ics and make_lbcs
    # tasks (i.e. tasks involving chgres_cube) to work.
    #
    elif file_group == "sfc_climo":
        fns = []
        for sfc_climo_field in sfc_climo_fields:
            fns.append(f"C*.{sfc_climo_field}.tile{tile_rgnl}.halo{nh0}.nc")
            fns.append(f"C*.{sfc_climo_field}.tile{tile_rgnl}.halo{nh4}.nc")

    fps = [os.path.join(source_dir, itm) for itm in fns]
    #
    # -----------------------------------------------------------------------
    #
    # Find all files matching the globbing patterns and make sure that they
    # all have the same resolution (an integer) in their names.
    #
    # -----------------------------------------------------------------------
    #
    i = 0
    res_prev = ""
    res = ""
    fp_prev = ""

    for pattern in fps:
        files = glob.glob(pattern)
        if not files:
            print_err_msg_exit(
                f"""
                Trying to link files in group: {file_group} 
                No files were found matching the pattern {pattern}.
                """
            )
        for fp in files:

            fn = os.path.basename(fp)

            regex_search = "^C([0-9]*).*"
            res = find_pattern_in_str(regex_search, fn)
            if not res:
                print_err_msg_exit(
                    f"""
                    The resolution could not be extracted from the current file's name.  The
                    full path to the file (fp) is:
                      fp = '{fp}'
                    This may be because fp contains the * globbing character, which would
                    imply that no files were found that match the globbing pattern specified
                    in fp."""
                )
            else:
                res = res[0]

            if (i > 0) and (res != res_prev):
                print_err_msg_exit(
                    f"""
                    The resolutions (as obtained from the file names) of the previous and
                    current file (fp_prev and fp, respectively) are different:
                      fp_prev = '{fp_prev}'
                      fp      = '{fp}'
                    Please ensure that all files have the same resolution."""
                )

            i = i + 1
            fp_prev = f"{fp}"
            res_prev = res
    #
    # -----------------------------------------------------------------------
    #
    # Replace the * globbing character in the set of globbing patterns with
    # the resolution.  This will result in a set of (full paths to) specific
    # files.
    #
    # -----------------------------------------------------------------------
    #
    fps = [itm.replace("*", res) for itm in fps]
    #
    # -----------------------------------------------------------------------
    #
    # In creating the various symlinks below, it is convenient to work in
    # the FIXlam directory.  We will change directory back to the original
    # later below.
    #
    # -----------------------------------------------------------------------
    #
    save_dir = os.getcwd()
    cd_vrfy(target_dir)
    #
    # -----------------------------------------------------------------------
    #
    # Use the set of full file paths generated above as the link targets to
    # create symlinks to these files in the target directory.
    #
    # -----------------------------------------------------------------------
    #
    # If the task in consideration (one of the pre-processing tasks
    # TN_MAKE_GRID, TN_MAKE_OROG, and TN_MAKE_SFC_CLIMO) was run, then
    # the source location of the fix files will be located under the
    # experiment directory.  In this case, we use relative symlinks for
    # portability and readability. Make absolute links otherwise.
    #
    relative_link_flag = False
    if run_task:
        relative_link_flag = True

    for fp in fps:
        fn = os.path.basename(fp)
        create_symlink_to_file(fp, fn, relative_link_flag)
    #
    # -----------------------------------------------------------------------
    #
    # Set the C-resolution based on the resolution appearing in the file
    # names.
    #
    # -----------------------------------------------------------------------
    #
    cres = f"C{res}"
    #
    # -----------------------------------------------------------------------
    #
    # If considering grid files, create a symlink to the halo4 grid file
    # that does not contain the halo size in its name.  This is needed by
    # the tasks that generate the initial and lateral boundary condition
    # files.
    #
    # -----------------------------------------------------------------------
    #
    if file_group == "grid":
        target = f"{cres}{dot_or_uscore}grid.tile{tile_rgnl}.halo{nh4}.nc"
        symlink = f"{cres}{dot_or_uscore}grid.tile{tile_rgnl}.nc"
        create_symlink_to_file(target, symlink, True)
    #
    # -----------------------------------------------------------------------
    #
    # If considering surface climatology files, create symlinks to the surface
    # climatology files that do not contain the halo size in their names.
    # These are needed by the make_ics task.
    #
    # The forecast model needs sfc climo files to be named without the
    # tile7 and halo references, and with only "tile1" in the name.
    #
    # -----------------------------------------------------------------------
    #
    if file_group == "sfc_climo":

        for field in sfc_climo_fields:

            # Create links without "halo" in the name
            halo = f"{cres}.{field}.tile{tile_rgnl}.halo{nh4}.nc"
            no_halo = re.sub(f".halo{nh4}", "", halo)
            create_symlink_to_file(halo, no_halo, True)

            # Create links without halo and tile7, and with "tile1"
            halo_tile = f"{cres}.{field}.tile{tile_rgnl}.halo{nh0}.nc"
            no_halo_tile = re.sub(f"tile{tile_rgnl}.halo{nh0}", "tile1", halo_tile)
            create_symlink_to_file(halo_tile, no_halo_tile, True)

    # Change directory back to original one.
    cd_vrfy(save_dir)

    return res


def parse_args(argv):
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Creates symbolic links to FIX directories."
    )

    parser.add_argument(
        "-f",
        "--file-group",
        dest="file_group",
        required=True,
        help='File group, could be one of ["grid", "orog", "sfc_climo"].',
    )

    parser.add_argument(
        "-p",
        "--path-to-defns",
        dest="path_to_defns",
        required=True,
        help="Path to var_defns file.",
    )

    return parser.parse_args(argv)


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    cfg = load_shell_config(args.path_to_defns)
    link_fix(
        verbose=cfg["workflow"]["VERBOSE"],
        file_group=args.file_group,
        source_dir=cfg[f"task_make_{args.file_group.lower()}"][
            f"{args.file_group.upper()}_DIR"
        ],
        target_dir=cfg["workflow"]["FIXlam"],
        ccpp_phys_suite=cfg["workflow"]["CCPP_PHYS_SUITE"],
        constants=cfg["constants"],
        dot_or_uscore=cfg["workflow"]["DOT_OR_USCORE"],
        nhw=cfg["grid_params"]["NHW"],
        run_task=True,
        sfc_climo_fields=cfg["fixed_files"]["SFC_CLIMO_FIELDS"],
    )


class Testing(unittest.TestCase):
    def test_link_fix(self):
        res = link_fix(
            verbose=True,
            file_group="grid",
            source_dir=self.task_dir,
            target_dir=self.FIXlam,
            ccpp_phys_suite=self.cfg["CCPP_PHYS_SUITE"],
            constants=self.cfg["constants"],
            dot_or_uscore=self.cfg["DOT_OR_USCORE"],
            nhw=self.cfg["NHW"],
            run_task=False,
            sfc_climo_fields=["foo", "bar"],
        )
        self.assertTrue(res == "3357")

    def setUp(self):
        define_macos_utilities()
        TEST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_data")
        self.FIXlam = os.path.join(TEST_DIR, "expt", "fix_lam")
        self.task_dir = os.path.join(TEST_DIR, "RRFS_CONUS_3km")
        mkdir_vrfy("-p", self.FIXlam)

        self.cfg = {
            "DOT_OR_USCORE": "_",
            "NHW": 6,
            "CCPP_PHYS_SUITE": "FV3_GSD_SAR",
            "constants": {
                "NH0": 0,
                "NH4": 4,
                "NH3": 3,
                "TILE_RGNL": 7,
            },
        }
