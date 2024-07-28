import React from 'react';
import { StreamlitComponentBase, Streamlit, withStreamlitConnection, ComponentProps} from 'streamlit-component-lib';
import toWav from 'audiobuffer-to-wav';
import './styles.css';
import tinycolor from 'tinycolor2'

interface State {
    recording: boolean;
    isHovered: boolean;
    isPlaying: boolean,
}

class MicRecorder extends StreamlitComponentBase<State> {

    private mediaRecorder1?: MediaRecorder;
	private mediaRecorder2?: MediaRecorder;
    private audioChunks1: Blob[] = [];
	private audioChunks2: Blob[] = [];
    private output?: object;
    private counter = 0;
    private activeRecorder1 = false;
    private activeRecorder2 = false;
	private timer?: number;

    public state: State = {
        recording: false,
        isHovered: false,
        isPlaying: false,
    };

    private handlePlay = (event: Event) => {
        console.log("Audio player started.");
        this.setState({ isPlaying: true });
        if(this.state.recording){
            clearTimeout(this.timer)
            try{
                this.mediaRecorder1?.pause()
            }catch(error){}
            try{
                this.mediaRecorder2?.pause()
            }catch(error){}
        }
        Streamlit.setComponentValue({type: "player", value: "started", id: Date.now()});
        console.log("Audio player started finished handler.");
    }

    private handleEnded = (event: Event) => {
        console.log("Audio player ended.");
        this.setState({ isPlaying: false });
        if(this.state.recording){
            try{
                this.mediaRecorder1?.resume()
            }catch(error){}
            try{
                this.mediaRecorder2?.resume()
            }catch(error){}
            this.loop(this.props.args["audio_chunk_time"])
        }
        Streamlit.setComponentValue({type: "player", value: "ended", id: Date.now()});
        console.log("Audio player started finished handler.");
    }

    public constructor(props: ComponentProps) {
	    console.log("Constructor.");
        super(props)
        const players = window.parent.document.getElementsByTagName('audio');
        if (players.length > 0){
            const player = players[0];
            player.addEventListener("play", this.handlePlay);
            player.addEventListener("ended", this.handleEnded);
        }
    }

    private handleMouseEnter = () => {
        this.setState({ isHovered: true });
    }
    
    private handleMouseLeave = () => {
        this.setState({ isHovered: false });
    }

    public componentDidMount(): void {
        super.componentDidMount()
        //console.log("Component mounted")
    }

    private buttonStyle = (Theme:any):React.CSSProperties => {
        const baseBorderColor = tinycolor.mix(Theme.textColor, Theme.backgroundColor, 80).lighten(2).toString();
        const backgroundColor = tinycolor.mix(Theme.textColor, tinycolor.mix(Theme.primaryColor, Theme.backgroundColor, 99), 99).lighten(0.5).toString();
        const textColor = this.state.isHovered ? Theme.primaryColor : Theme.textColor;
        const borderColor = this.state.isHovered ? Theme.primaryColor : baseBorderColor;
        
        return {
            ...this.props.args["use_container_width"] ? { width: '100%' } : {},
            borderColor: borderColor,
            backgroundColor: backgroundColor,
            color: textColor
        };
    }

    private onClick =()=>{
        if(!this.state.isPlaying){
            this.state.recording ? (
                this.stopRecording()
            ):(
                this.startRecording()
            )
        }
    }

    private buttonPrompt=()=>{
        return (
			this.state.recording ? (
				this.props.args["stop_prompt"]
			):(
				this.props.args["start_prompt"]
			)
        )
    }

    public render(): React.ReactNode {
        console.log("Component renders");
        const Theme = this.props.theme ?? {
            base: 'dark',
            backgroundColor: 'black',
            secondaryBackgroundColor: 'grey',
            primaryColor: 'red',
            textColor: 'white'
        };

        return (
            <div className="App">
                <button 
                    className="myButton" 
                    style={this.buttonStyle(Theme)} 
                    onClick={this.onClick}
                    onMouseEnter={this.handleMouseEnter}
                    onMouseLeave={this.handleMouseLeave}
                >
                    {this.buttonPrompt()}
                </button>
            </div>
        );
    }
	
	private loop(timeout:number) {
		this.timer = window.setTimeout(() => {
		    console.log("Timeout", this.counter)
			const half_count = Math.floor(this.props.args["audio_chunks_number"]/2);
			if (this.activeRecorder1){
			    //console.log("Request1");
                this.mediaRecorder1?.requestData();
            }
            else{
                //console.log("Request2");
                this.mediaRecorder2?.requestData();
            }
			if(this.counter === half_count){
                if (this.activeRecorder1){
                    //console.log("Start2");
                    this.audioChunks2 = [];
                    this.mediaRecorder2?.start();
                }
                else{
                    //console.log("Start1");
                    this.audioChunks1 = [];
                    this.mediaRecorder1?.start();
                }
            }
            if(this.counter === this.props.args["audio_chunks_number"]){
                if (this.activeRecorder1){
                    //console.log("Stop1");
                    this.mediaRecorder1?.stop();
                    this.activeRecorder1 = false;
                    this.activeRecorder2 = true;
                }
                else{
                    //console.log("Stop2");
                    this.mediaRecorder2?.stop();
                    this.activeRecorder1 = true;
                    this.activeRecorder2 = false;
                }
                this.counter = 0;
            }
            else{
                this.counter++;
            }
			this.loop(this.props.args["audio_chunk_time"]);
		}, timeout);
	}

    private startRecording = () => {
        //console.log("Component starts recording");
        Streamlit.setComponentValue({type: "button", value: "start", id: Date.now()});
        if((this.mediaRecorder1)&&(this.mediaRecorder2)){
            this.audioChunks1 = [];
			this.audioChunks2 = [];
            this.counter=0;
            this.activeRecorder1 = true;
            this.activeRecorder2 = false;
            this.mediaRecorder1.start();
            this.setState({ recording: true });
			this.loop(this.props.args["audio_min_start_time"])
        }
        else{
            navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1 } }).then(stream => {
                this.mediaRecorder1 = new MediaRecorder(stream);
				this.mediaRecorder2 = new MediaRecorder(stream);

                this.mediaRecorder1.ondataavailable = event => {
                    if (event.data) {
                        //console.log("Event1", this.counter);
						this.audioChunks1.push(event.data);
						if(this.activeRecorder1){
						    //console.log("Send1")
						    this.processAndSendRecording(this.audioChunks1, 1, this.counter);
                        }
                    }
                }

				this.mediaRecorder2.ondataavailable = event => {
                    if (event.data) {
                        //console.log("Event2", this.counter);
						this.audioChunks2.push(event.data);
						if(this.activeRecorder2){
						    //console.log("Send2")
                            this.processAndSendRecording(this.audioChunks2, 2, this.counter);
                        }
                    }
                }

                this.mediaRecorder1.onerror = (event) => {
                    //console.error("MediaRecorder1 error: ", event);
                }

				this.mediaRecorder2.onerror = (event) => {
                    //console.error("MediaRecorder2 error: ", event);
                }

                this.mediaRecorder1.onstop = (event) => {
                    //console.log("Stopped1");
                    this.processAndSendRecording(this.audioChunks1, 1, this.counter);
                }

                this.mediaRecorder2.onstop = (event) => {
                    //console.log("Stopped2");
                    this.processAndSendRecording(this.audioChunks2, 2, this.counter);
                }

                this.audioChunks1 = [];
                this.audioChunks2 = [];
                this.counter=0;
                this.activeRecorder1 = true;
                this.activeRecorder2 = false;
                this.mediaRecorder1.start();
				this.setState({ recording: true });
				this.loop(this.props.args["audio_min_start_time"])
            }).catch(error => {
                //console.error("Error initializing media recording: ", error);
            });
        }
    }

    private stopRecording = async () => {
		//console.log("Component stops recording");
		this.setState({ recording: false });
		clearTimeout(this.timer);
		this.activeRecorder1 = false;
        this.activeRecorder2 = false;
		this.mediaRecorder1?.stop();
		this.mediaRecorder2?.stop();
		Streamlit.setComponentValue({type: "button", value: "stop", id: Date.now()});
    }

    private processRecording = async (chunks:any, recorder:number, counter:number) => {
        //console.log("Component processing the recording...");
        return new Promise<void>(async (resolve) => {
            //console.log(chunks);
            const audioBlob = new Blob(chunks, { type: this.mediaRecorder1?.mimeType || 'audio/webm' });
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const arrayBuffer = await audioBlob.arrayBuffer();
            const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
            const sampleRate = audioBuffer.sampleRate;

            // For WebM, you can directly prepare the data to send
            if (this.props.args['format'] === 'webm') {
                const reader = new FileReader();
                reader.onloadend = () => {
                    const base64String = reader.result?.toString().split(',')[1];
                    this.output = {
                        type: "audio",
                        id: Date.now(),
                        format:"webm",
                        audio_base64: base64String,
                        sample_rate: sampleRate,
                        sample_width: 2,
                        cycle: [recorder, counter]
                    }
                    resolve();
                }
                reader.readAsDataURL(audioBlob);
            } else if (this.props.args['format'] === 'wav') {

                const wav: ArrayBuffer = toWav(audioBuffer);
                const reader = new FileReader();
                reader.onloadend = () => {
                    const base64String = reader.result?.toString().split(',')[1];
                    this.output = {
                        type: "audio",
                        id:Date.now(),
                        format:"wav",
                        audio_base64: base64String,
                        sample_rate: sampleRate,
                        sample_width: 2,
                        cycle: [recorder, counter]
                    }
                    resolve();
                }
                reader.readAsDataURL(new Blob([wav], { type: 'audio/wav' }));
            }
        });
    }

    private sendDataToStreamlit = () => {
        //console.log("Sending data to streamlit...")
        if (this.output) {
            Streamlit.setComponentValue(this.output);
        }
    }

    private processAndSendRecording = async (chunks:any, recorder:number, counter:number) => {
        await this.processRecording(chunks, recorder, counter);
        //console.log("Processing finished")
        this.sendDataToStreamlit();
        //console.log("Data sent to Streamlit")
        this.output=undefined;
    }
}

export default withStreamlitConnection(MicRecorder);