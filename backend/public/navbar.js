//Reuseable navbar

const template = document.createElement('template');

template.innerHTML = `
	<style>
		.navbar{
			width: 80%;
			height: 4rem;
			display: flex;
			justify-content:space-between;
			align-items: center;
			margin: 1.5rem;
			gap: 2rem;
		}

		.navbar > div {
			align-items: center;
			justify-content: center;
		}

		.item1 {
			align-self
		}

		.nav-container{
			display: flex;
			flex-direction: row;
			justify-item: center;
			align-self: center;
			align-items: center;
			padding: 1.5rem;
			gap: 1rem;
		}

		.route {
			font-size: 1rem;
			padding: 10px;
			border: 2px solid rgba(255, 255, 255, 0.1);
			border-radius: 50px;
			text-decoration: none;
			color: white;
		}

		.route:hover{
			background: linear-gradient(135deg, #8b5cf6, #3b82f6, #06b6d4);
		}
	</style>

	<header class="navbar">
	    <div class="itemq">
			<h1>P2P Storage Network</h1>
	    </div>
	    <div class="item">
		    <div class="nav-container">
	         	<a class="route" href="/">Dashboard</a>
		        <a class="route" href="/plans">Upgrade Storage</a>
		    </div>
	    </div>
	    <div class="item">
 			<p>Wallet Demo</p>
    	</div>
    </header>
    `

class ReuseableNav extends HTMLElement {
	constructor() {
		super()
		this.attachShadow({ mode: 'open' })
		this.shadowRoot.appendChild(template.content.cloneNode(true))
	}

}

customElements.define('reuseable-nav', ReuseableNav);
