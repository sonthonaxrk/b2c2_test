/**
 * This was created because Jupyter does not
 * have any mechanisms for controlling the creation
 * of new cells.
 */
define([
    'base/js/namespace'
], function(
    Jupyter
) {

    function create_cell(msg) {
        var cell = Jupyter.notebook.insert_cell_at_bottom('code');
        cell.set_text(msg.content.data.code);
        if (msg.content.data.execute) {
            cell.execute();
        }
    }

    function load_ipython_extension() {
        // Register target is called *every* time
        // a Comm class is created (in python). But it upserts
        // the old handler.
        debugger;
        Jupyter.notebook.kernel.comm_manager.register_target(
            'create_cell',
            function(comm, msg) {
                comm.on_msg(create_cell)
                // This just tells the listener
                // in the kernel that the extension
                // has been loaded. This way we can
                // verify the extension is active
                comm.send({
                    'setup': true
                });
            }
        );
    }

    return {
        load_ipython_extension: load_ipython_extension
    };
});
