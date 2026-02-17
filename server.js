// server.js
require('dotenv').config();
const express = require('express');
const cors = require('cors');
const Stripe = require('stripe');
const bodyParser = require('body-parser');

const app = express();
const stripe = Stripe(process.env.STRIPE_SECRET_KEY);

// Middleware
app.use(cors());
app.use((req, res, next) => {
  if (req.originalUrl === '/webhook') {
    next(); // Skip JSON parse for webhook
  } else {
    express.json()(req, res, next);
  }
});

// --- DATA CONFIGURATION (Your Models) ---
const MODELS = {
  image: [
    { id: 'fluxon-2', name: 'Fluxon 2.0', cost: 2, tier: 'Fast' },
    { id: 'kling-o1', name: 'Kling O1', cost: 2, tier: 'Fast' },
    { id: 'midjourney-v7', name: 'Midjourney V7', cost: 3, tier: 'Professional' },
    { id: 'nano-banana', name: 'Nano Banana Pro', cost: 15, tier: 'Reference Master' }
    // ... add all other image models here
  ],
  video: [
    { id: 'lumen-fast', name: 'Lumen 2.3 Fast', cost: 10, tier: 'Budget' },
    { id: 'veo-3', name: 'Google Veo 3.1', cost: 100, tier: 'Premium' },
    { id: 'sora-2-pro', name: 'Sora 2 Pro', cost: 150, tier: 'Ultra Elite' }
    // ... add all other video models here
  ]
};

// --- ROUTES ---

// 1. Get Available Models
app.get('/api/models', (req, res) => {
  res.json(MODELS);
});

// 2. Generate Image (Mock)
app.post('/api/generate-image', async (req, res) => {
  const { modelId, prompt, userId } = req.body;
  // TODO: Check user credits in database here
  // TODO: Call actual API (Flux, Midjourney, etc.)
  
  // Mock Response for now
  res.json({ 
    success: true, 
    imageUrl: "https://via.placeholder.com/1024", 
    creditsDeducted: MODELS.image.find(m => m.id === modelId).cost 
  });
});

// 3. Create Checkout Session (Stripe)
app.post('/api/create-checkout-session', async (req, res) => {
  const { plan } = req.body;
  
  let priceId;
  // Map your plans to Stripe Price IDs (You get these from Stripe Dashboard)
  switch(plan) {
    case 'Lite': priceId = 'price_LITE_ID_FROM_STRIPE'; break;
    case 'Standard': priceId = 'price_STANDARD_ID_FROM_STRIPE'; break;
    case 'Pro': priceId = 'price_PRO_ID_FROM_STRIPE'; break;
    case 'Ultra': priceId = 'price_ULTRA_ID_FROM_STRIPE'; break;
  }

  const session = await stripe.checkout.sessions.create({
    payment_method_types: ['card'],
    line_items: [{ price: priceId, quantity: 1 }],
    mode: 'subscription',
    success_url: `${process.env.CLIENT_URL}/success?session_id={CHECKOUT_SESSION_ID}`,
    cancel_url: `${process.env.CLIENT_URL}/pricing`,
  });

  res.json({ url: session.url });
});

// 4. Stripe Webhook (To update credits after payment)
app.post('/webhook', bodyParser.raw({type: 'application/json'}), (request, response) => {
  const sig = request.headers['stripe-signature'];
  let event;

  try {
    event = stripe.webhooks.constructEvent(request.body, sig, process.env.STRIPE_WEBHOOK_SECRET);
  } catch (err) {
    return response.status(400).send(`Webhook Error: ${err.message}`);
  }

  // Handle the event
  if (event.type === 'checkout.session.completed') {
    const session = event.data.object;
    // TODO: Add credits to user database based on amount_total
    console.log("Payment successful! Add credits to user.");
  }

  response.send();
});

const PORT = process.env.PORT || 5000;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));