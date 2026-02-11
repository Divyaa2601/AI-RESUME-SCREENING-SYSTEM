document.getElementById('resumeInput').addEventListener('change', function() {
    const fileNames = Array.from(this.files).map(f => f.name).join(', ');
    document.getElementById('fileNames').innerText = fileNames;
});
