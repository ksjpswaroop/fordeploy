// Smooth rich classic color gradients derived from user list
export interface GradientDef { name: string; from: string; to: string; mid?: string; }

export const GRADIENTS: GradientDef[] = [
  { name: 'Indigo Mist', from: '#4F5BD5', to: '#9FA8F8' },
  { name: 'Deep Ocean', from: '#0F4C81', to: '#3FA9D6' },
  { name: 'Sapphire Fade', from: '#1E3A8A', to: '#60A5FA' },
  { name: 'Emerald Glow', from: '#0F6B4F', to: '#4FD4A1' },
  { name: 'Forest Velvet', from: '#144D38', to: '#3F9E72' },
  { name: 'Teal Breeze', from: '#0F5F66', to: '#4FC9D3' },
  { name: 'Golden Amber', from: '#B7791F', to: '#F6C760' },
  { name: 'Warm Honey', from: '#A86514', to: '#E8B467' },
  { name: 'Rose Quartz', from: '#B43A55', to: '#F28CA3' },
  { name: 'Coral Sunset', from: '#C75147', to: '#FF9A7A' },
  { name: 'Plum Aura', from: '#5B2B66', to: '#B779D6' },
  { name: 'Violet Silk', from: '#55309C', to: '#B19BFF' },
  { name: 'Burgundy Reserve', from: '#5C1F2D', to: '#B35663' },
  { name: 'Copper Clay', from: '#6B3B26', to: '#C68A5D' },
  { name: 'Slate Steel', from: '#2E3A47', to: '#7B8B97' },
  { name: 'Graphite Soft', from: '#3A3F45', to: '#8E959C' },
  { name: 'Midnight Navy', from: '#0F172A', to: '#465270' },
  { name: 'Charcoal Fade', from: '#1E242A', to: '#4B545D' },
  { name: 'Soft Sand', from: '#D9C7B2', to: '#F2E7D8' },
  { name: 'Porcelain Light', from: '#E8ECEF', to: '#FFFFFF' }
];

export function pickGradient(i:number){ return GRADIENTS[i % GRADIENTS.length]; }
