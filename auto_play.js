const players = window.parent.document.getElementsByTagName('audio');
if (players.length > 0){
    console.log("Audio play.");
    const player = players[0];
    player.play();
}