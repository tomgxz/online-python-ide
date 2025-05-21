const run_code = async function() {
    const code = EDITOR.getValue();
    const deps = input_dependencies.val().split(" ").filter(x => x);

    output_wrapper.text('');
    button_run.text("Running");

    let ellipsis = '';

    ellipsisInterval = setInterval(() => {
        ellipsis = ellipsis.length < 3 ? ellipsis + '.' : '';
        button_run.text("Running" + ellipsis);
    }, 200);
    
    const response = await fetch("/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code, dependencies: deps })
    });

    if (!response.body) {
        output_wrapper.text('No response body.');
        clearInterval(ellipsisInterval);
        button_run.text("Run");
        return;
    }
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
        const { value, done } = await reader.read();
        if (done) {
            clearInterval(ellipsisInterval);
            button_run.text("Run");
            break;
        }

        output_wrapper.text(output_wrapper.text() + decoder.decode(value, { stream: true }));
        output_wrapper.scrollTop(output_wrapper[0].scrollHeight);
    }
}


const button_run = $("#button_run"),
      input_dependencies = $("#input_dependencies"),
      output_wrapper = $("#output_wrapper");

var EDITOR;


$(window).load(function() {
    EDITOR = CodeMirror.fromTextArea(document.getElementById('editor'), {
        mode: 'python',
        lineNumbers: true
    });
    
    button_run.on("click", run_code);
});
