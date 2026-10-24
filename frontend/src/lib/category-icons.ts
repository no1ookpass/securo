import type { LucideIcon } from 'lucide-react'
import type { TFunction } from 'i18next'
// Whole-namespace import powers the "everything else" block at the bottom that
// offers the complete Lucide library (see the bundle note there).
import * as LucideIcons from 'lucide-react'
import {
  House, UtensilsCrossed, Car, ShoppingCart, Pill, Gamepad2, Smartphone, BookOpen, ArrowLeftRight, CircleHelp,
  Wallet, CreditCard, Banknote, PiggyBank, TrendingUp, TrendingDown, Receipt, ShoppingBag, Gift, Heart,
  Baby, Dog, Cat, Plane, Train, Bus, Fuel, Bike, Lightbulb, Droplets,
  Flame, Wifi, Tv, GraduationCap, Briefcase, Building2, Landmark, Dumbbell, Shirt, Scissors,
  Wrench, Hammer, Music, Film, Coffee, Beer, Pizza, Salad, Stethoscope, Syringe,
  Cross, PartyPopper, TreePine, Umbrella, Globe, Sparkles, HeartHandshake, Brain, HandCoins, Ticket,
  Sofa, SprayCan, Package, BedDouble, Luggage, School, Trophy, Camera, Newspaper, Laptop,
  Monitor, Trees, Croissant, Cake, IceCreamCone, Apple, Beef, Fish, Motorbike, CarTaxiFront,
  PencilRuler, Refrigerator, PawPrint,
  // Expanded glyph set (fork)
  Sandwich, ChefHat, Cookie, Martini, Milk, Citrus, Grape, Drumstick, Egg, Wheat,
  CupSoda, Soup, Popcorn, Candy, Wine, Donut, Hamburger, Dessert, CookingPot, ShoppingBasket,
  Store, Tag, Percent, Box, Gem, Crown, Handbag, CarFront, TramFront, TrainFront,
  Ship, Anchor, Rocket, CircleParking, Map, HeartPulse, Activity, Bone, Ear, Ambulance,
  ClipboardPlus, PlugZap, Lamp, Fan, Snowflake, ShowerHead, Bath, Ruler, Paintbrush, PaintRoller,
  KeyRound, DoorOpen, Armchair, Fence, Sprout, Flower2, Recycle, Dices, Clapperboard, Drama,
  Mic2, Piano, Palette, MonitorPlay, Library, Balloon, Tent, TentTree, Mountain, Waves,
  Sun, Footprints, Coins, CircleDollarSign, BadgeDollarSign, ChartLine, ChartPie, ChartColumn, PieChart, LineChart,
  BarChart3, BriefcaseBusiness, ReceiptText, Scale, CirclePercent, CandlestickChart, BookMarked, PencilLine, Printer, Factory,
  Drill, HardHat, Truck, PackageCheck, Tablet, Watch, Headphones, Radio, Cloud, Database,
  Server, Cpu, BatteryCharging, Repeat, RefreshCw, Bird, Rabbit, Users, Star, Flag,
  Medal, Award, Earth, MapPin, Compass, Clock, CalendarDays, Info, TriangleAlert, ShieldCheck,
  Shield, Fingerprint
} from 'lucide-react'

export interface CategoryIconEntry {
  name: string      // Lucide icon name (stored in DB)
  pt: string        // Portuguese label, used as fallback when a locale has no translation
  icon: LucideIcon  // Component reference
}

export const CATEGORY_ICONS: CategoryIconEntry[] = [
  // Moradia & Casa
  { name: 'house', pt: 'Casa / Moradia', icon: House },
  { name: 'lightbulb', pt: 'Luz / Energia', icon: Lightbulb },
  { name: 'droplets', pt: 'Água', icon: Droplets },
  { name: 'flame', pt: 'Gás', icon: Flame },
  { name: 'wifi', pt: 'Internet / Wi-Fi', icon: Wifi },
  { name: 'tv', pt: 'TV / Streaming', icon: Tv },
  { name: 'refrigerator', pt: 'Eletrodomésticos', icon: Refrigerator },
  { name: 'sofa', pt: 'Móveis / Decoração', icon: Sofa },
  { name: 'spray-can', pt: 'Limpeza / Diarista', icon: SprayCan },
  // Alimentação
  { name: 'utensils-crossed', pt: 'Alimentação / Restaurante', icon: UtensilsCrossed },
  { name: 'coffee', pt: 'Café', icon: Coffee },
  { name: 'beer', pt: 'Bebidas / Bar', icon: Beer },
  { name: 'pizza', pt: 'Pizza / Fast Food', icon: Pizza },
  { name: 'salad', pt: 'Salada / Saudável', icon: Salad },
  { name: 'croissant', pt: 'Padaria / Pão', icon: Croissant },
  { name: 'cake', pt: 'Doces / Confeitaria', icon: Cake },
  { name: 'ice-cream-cone', pt: 'Sorvete / Sobremesa', icon: IceCreamCone },
  { name: 'apple', pt: 'Feira / Hortifruti', icon: Apple },
  { name: 'beef', pt: 'Açougue / Carnes', icon: Beef },
  { name: 'fish', pt: 'Peixaria / Frutos do mar', icon: Fish },
  // Transporte
  { name: 'car', pt: 'Carro / Transporte', icon: Car },
  { name: 'fuel', pt: 'Combustível / Gasolina', icon: Fuel },
  { name: 'bus', pt: 'Ônibus', icon: Bus },
  { name: 'train', pt: 'Trem / Metrô', icon: Train },
  { name: 'plane', pt: 'Avião / Viagem', icon: Plane },
  { name: 'bike', pt: 'Bicicleta', icon: Bike },
  { name: 'motorbike', pt: 'Moto', icon: Motorbike },
  { name: 'car-taxi-front', pt: 'Táxi / App de corrida', icon: CarTaxiFront },
  { name: 'bed-double', pt: 'Hospedagem / Hotel', icon: BedDouble },
  { name: 'luggage', pt: 'Bagagem / Mala', icon: Luggage },
  // Compras
  { name: 'shopping-cart', pt: 'Mercado / Supermercado', icon: ShoppingCart },
  { name: 'shopping-bag', pt: 'Compras / Loja', icon: ShoppingBag },
  { name: 'gift', pt: 'Presente', icon: Gift },
  { name: 'package', pt: 'Compra online / Entrega', icon: Package },
  { name: 'shirt', pt: 'Roupa / Vestuário', icon: Shirt },
  // Saúde
  { name: 'pill', pt: 'Remédio / Farmácia', icon: Pill },
  { name: 'stethoscope', pt: 'Médico / Consulta', icon: Stethoscope },
  { name: 'syringe', pt: 'Vacina / Exame', icon: Syringe },
  { name: 'cross', pt: 'Hospital / Emergência', icon: Cross },
  { name: 'heart', pt: 'Saúde / Bem-estar', icon: Heart },
  { name: 'brain', pt: 'Saúde mental / Terapia', icon: Brain },
  { name: 'dumbbell', pt: 'Academia / Exercício', icon: Dumbbell },
  // Lazer
  { name: 'gamepad-2', pt: 'Jogos / Lazer', icon: Gamepad2 },
  { name: 'music', pt: 'Música', icon: Music },
  { name: 'film', pt: 'Cinema / Filme', icon: Film },
  { name: 'party-popper', pt: 'Festa / Evento', icon: PartyPopper },
  { name: 'ticket', pt: 'Ingresso / Eventos', icon: Ticket },
  { name: 'trophy', pt: 'Esporte / Competição', icon: Trophy },
  { name: 'camera', pt: 'Fotografia / Câmera', icon: Camera },
  { name: 'newspaper', pt: 'Jornal / Revista', icon: Newspaper },
  // Tecnologia & Assinaturas
  { name: 'smartphone', pt: 'Celular / Telefone', icon: Smartphone },
  { name: 'credit-card', pt: 'Cartão de Crédito', icon: CreditCard },
  { name: 'laptop', pt: 'Notebook / Tablet', icon: Laptop },
  { name: 'monitor', pt: 'Computador / Periféricos', icon: Monitor },
  // Educação
  { name: 'book-open', pt: 'Livro / Leitura', icon: BookOpen },
  { name: 'graduation-cap', pt: 'Educação / Curso', icon: GraduationCap },
  { name: 'school', pt: 'Escola / Mensalidade escolar', icon: School },
  { name: 'pencil-ruler', pt: 'Papelaria / Material escolar', icon: PencilRuler },
  // Trabalho & Negócios
  { name: 'briefcase', pt: 'Trabalho / Negócios', icon: Briefcase },
  { name: 'building-2', pt: 'Empresa / Escritório', icon: Building2 },
  { name: 'landmark', pt: 'Banco / Governo', icon: Landmark },
  // Finanças
  { name: 'wallet', pt: 'Carteira', icon: Wallet },
  { name: 'banknote', pt: 'Dinheiro', icon: Banknote },
  { name: 'piggy-bank', pt: 'Poupança / Investimento', icon: PiggyBank },
  { name: 'trending-up', pt: 'Rendimento / Lucro', icon: TrendingUp },
  { name: 'trending-down', pt: 'Prejuízo / Perda', icon: TrendingDown },
  { name: 'hand-coins', pt: 'Empréstimo / Dívida', icon: HandCoins },
  { name: 'receipt', pt: 'Recibo / Nota Fiscal', icon: Receipt },
  { name: 'arrow-left-right', pt: 'Transferência', icon: ArrowLeftRight },
  { name: 'heart-handshake', pt: 'Doação / Solidariedade', icon: HeartHandshake },
  // Família & Pets
  { name: 'baby', pt: 'Bebê / Criança', icon: Baby },
  { name: 'dog', pt: 'Pet / Cachorro', icon: Dog },
  { name: 'cat', pt: 'Pet / Gato', icon: Cat },
  { name: 'paw-print', pt: 'Pet / Geral', icon: PawPrint },
  // Serviços & Manutenção
  { name: 'scissors', pt: 'Cabelo / Beleza', icon: Scissors },
  { name: 'wrench', pt: 'Manutenção / Reparo', icon: Wrench },
  { name: 'hammer', pt: 'Construção / Reforma', icon: Hammer },
  // Outros
  { name: 'tree-pine', pt: 'Natureza / Jardim', icon: TreePine },
  { name: 'trees', pt: 'Floresta / Natureza', icon: Trees },
  { name: 'umbrella', pt: 'Seguro', icon: Umbrella },
  { name: 'globe', pt: 'Internacional', icon: Globe },
  { name: 'sparkles', pt: 'Especial', icon: Sparkles },
  { name: 'circle-help', pt: 'Outros / Indefinido', icon: CircleHelp },
  // --- Expanded glyph set (fork) -------------------------------------------
  // Extra curated icons on top of the upstream catalogue, kept so they carry a
  // Portuguese label instead of the humanized name the catch-all block derives.
  { name: 'sandwich', pt: 'Sanduíche / Lanche', icon: Sandwich },
  { name: 'chef-hat', pt: 'Chef / Delivery', icon: ChefHat },
  { name: 'cookie', pt: 'Biscoito / Lanche', icon: Cookie },
  { name: 'martini', pt: 'Drinks / Coquetel', icon: Martini },
  { name: 'milk', pt: 'Leite / Mercado', icon: Milk },
  { name: 'citrus', pt: 'Frutas Cítricas', icon: Citrus },
  { name: 'grape', pt: 'Uvas / Vinho', icon: Grape },
  { name: 'drumstick', pt: 'Frango', icon: Drumstick },
  { name: 'egg', pt: 'Ovos / Café da Manhã', icon: Egg },
  { name: 'wheat', pt: 'Padaria / Farinha', icon: Wheat },
  { name: 'cup-soda', pt: 'Refrigerante', icon: CupSoda },
  { name: 'soup', pt: 'Sopa / Caldo', icon: Soup },
  { name: 'popcorn', pt: 'Cinema / Pipoca', icon: Popcorn },
  { name: 'candy', pt: 'Doces', icon: Candy },
  { name: 'wine', pt: 'Vinho / Bebida', icon: Wine },
  { name: 'donut', pt: 'Donut / Café', icon: Donut },
  { name: 'hamburger', pt: 'Lanchonete / Fast Food', icon: Hamburger },
  { name: 'dessert', pt: 'Sobremesa', icon: Dessert },
  { name: 'cooking-pot', pt: 'Culinária / Cozinha', icon: CookingPot },
  { name: 'shopping-basket', pt: 'Cestinha / Feira', icon: ShoppingBasket },
  { name: 'store', pt: 'Loja / Varejo', icon: Store },
  { name: 'tag', pt: 'Etiqueta / Promoção', icon: Tag },
  { name: 'percent', pt: 'Desconto / %', icon: Percent },
  { name: 'box', pt: 'Caixa', icon: Box },
  { name: 'gem', pt: 'Joia / Luxo', icon: Gem },
  { name: 'crown', pt: 'Premium / Assinatura', icon: Crown },
  { name: 'handbag', pt: 'Bolsa / Acessório', icon: Handbag },
  { name: 'car-front', pt: 'Carro (Frente)', icon: CarFront },
  { name: 'tram-front', pt: 'Bonde / Ônibus', icon: TramFront },
  { name: 'train-front', pt: 'Trem / Metrô', icon: TrainFront },
  { name: 'ship', pt: 'Navio / Cruzeiro', icon: Ship },
  { name: 'anchor', pt: 'Porto / Náutico', icon: Anchor },
  { name: 'rocket', pt: 'Startup / Alto Risco', icon: Rocket },
  { name: 'circle-parking', pt: 'Estacionamento', icon: CircleParking },
  { name: 'map', pt: 'Mapa / Rota', icon: Map },
  { name: 'heart-pulse', pt: 'Pulso / Cardiologia', icon: HeartPulse },
  { name: 'activity', pt: 'Atividade / Saúde', icon: Activity },
  { name: 'bone', pt: 'Ortopedia', icon: Bone },
  { name: 'ear', pt: 'Ouvido / Fono', icon: Ear },
  { name: 'ambulance', pt: 'Ambulância / Emergência', icon: Ambulance },
  { name: 'clipboard-plus', pt: 'Consulta / Exame', icon: ClipboardPlus },
  { name: 'plug-zap', pt: 'Energia / Recarga', icon: PlugZap },
  { name: 'lamp', pt: 'Lâmpada / Iluminação', icon: Lamp },
  { name: 'fan', pt: 'Ventilador / Ar', icon: Fan },
  { name: 'snowflake', pt: 'Ar-Condicionado', icon: Snowflake },
  { name: 'shower-head', pt: 'Água / Banho', icon: ShowerHead },
  { name: 'bath', pt: 'Banheiro', icon: Bath },
  { name: 'ruler', pt: 'Medidas / Reforma', icon: Ruler },
  { name: 'paintbrush', pt: 'Pintura', icon: Paintbrush },
  { name: 'paint-roller', pt: 'Reforma / Pintura', icon: PaintRoller },
  { name: 'key-round', pt: 'Chave / Aluguel', icon: KeyRound },
  { name: 'door-open', pt: 'Porta / Entrada', icon: DoorOpen },
  { name: 'armchair', pt: 'Sofá / Móveis', icon: Armchair },
  { name: 'fence', pt: 'Cerca / Jardim', icon: Fence },
  { name: 'sprout', pt: 'Plantas / Jardim', icon: Sprout },
  { name: 'flower-2', pt: 'Flores / Jardinagem', icon: Flower2 },
  { name: 'recycle', pt: 'Reciclagem / Lixo', icon: Recycle },
  { name: 'dices', pt: 'Jogos de Mesa', icon: Dices },
  { name: 'clapperboard', pt: 'Produção / Filme', icon: Clapperboard },
  { name: 'drama', pt: 'Teatro / Cultura', icon: Drama },
  { name: 'mic-2', pt: 'Karaokê / Música', icon: Mic2 },
  { name: 'piano', pt: 'Piano / Música', icon: Piano },
  { name: 'palette', pt: 'Arte / Criatividade', icon: Palette },
  { name: 'monitor-play', pt: 'Streaming / Vídeo', icon: MonitorPlay },
  { name: 'library', pt: 'Biblioteca', icon: Library },
  { name: 'balloon', pt: 'Festa / Decoração', icon: Balloon },
  { name: 'tent', pt: 'Acampamento', icon: Tent },
  { name: 'tent-tree', pt: 'Camping / Natureza', icon: TentTree },
  { name: 'mountain', pt: 'Trilha / Aventura', icon: Mountain },
  { name: 'waves', pt: 'Praia / Surfe', icon: Waves },
  { name: 'sun', pt: 'Verão / Sol', icon: Sun },
  { name: 'footprints', pt: 'Caminhada / Pet', icon: Footprints },
  { name: 'coins', pt: 'Moedas / Troco', icon: Coins },
  { name: 'circle-dollar-sign', pt: 'Dólar', icon: CircleDollarSign },
  { name: 'badge-dollar-sign', pt: 'Renda / US$', icon: BadgeDollarSign },
  { name: 'chart-line', pt: 'Gráfico / Análise', icon: ChartLine },
  { name: 'chart-pie', pt: 'Gráfico de Pizza', icon: ChartPie },
  { name: 'chart-column', pt: 'Gráfico de Barras', icon: ChartColumn },
  { name: 'pie-chart', pt: 'Gráfico de Pizza', icon: PieChart },
  { name: 'line-chart', pt: 'Gráfico de Linha', icon: LineChart },
  { name: 'bar-chart-3', pt: 'Gráfico de Barras', icon: BarChart3 },
  { name: 'briefcase-business', pt: 'Negócios / PJ', icon: BriefcaseBusiness },
  { name: 'receipt-text', pt: 'Nota / Recibo', icon: ReceiptText },
  { name: 'scale', pt: 'Impostos / Justiça', icon: Scale },
  { name: 'circle-percent', pt: 'Porcentagem', icon: CirclePercent },
  { name: 'candlestick-chart', pt: 'Ações / Investimento', icon: CandlestickChart },
  { name: 'book-marked', pt: 'Apostila / Estudo', icon: BookMarked },
  { name: 'pencil-line', pt: 'Edição / Anotações', icon: PencilLine },
  { name: 'printer', pt: 'Impressora', icon: Printer },
  { name: 'factory', pt: 'Fábrica / Indústria', icon: Factory },
  { name: 'drill', pt: 'Ferramenta / Furadeira', icon: Drill },
  { name: 'hard-hat', pt: 'Obra / Construção', icon: HardHat },
  { name: 'truck', pt: 'Caminhão / Frete', icon: Truck },
  { name: 'package-check', pt: 'Encomenda / Entrega', icon: PackageCheck },
  { name: 'tablet', pt: 'Tablet', icon: Tablet },
  { name: 'watch', pt: 'Relógio', icon: Watch },
  { name: 'headphones', pt: 'Fone / Áudio', icon: Headphones },
  { name: 'radio', pt: 'Rádio', icon: Radio },
  { name: 'cloud', pt: 'Nuvem / Armazenamento', icon: Cloud },
  { name: 'database', pt: 'Dados / Servidor', icon: Database },
  { name: 'server', pt: 'Servidor / Hosting', icon: Server },
  { name: 'cpu', pt: 'Hardware / TI', icon: Cpu },
  { name: 'battery-charging', pt: 'Recarga / Energia', icon: BatteryCharging },
  { name: 'repeat', pt: 'Assinatura / Recorrente', icon: Repeat },
  { name: 'refresh-cw', pt: 'Atualização / Renovação', icon: RefreshCw },
  { name: 'bird', pt: 'Pet / Pássaro', icon: Bird },
  { name: 'rabbit', pt: 'Pet / Coelho', icon: Rabbit },
  { name: 'users', pt: 'Família / Grupo', icon: Users },
  { name: 'star', pt: 'Favorito / Destaque', icon: Star },
  { name: 'flag', pt: 'Bandeira / País', icon: Flag },
  { name: 'medal', pt: 'Prêmio / Reconhecimento', icon: Medal },
  { name: 'award', pt: 'Premiação', icon: Award },
  { name: 'earth', pt: 'Mundo / Global', icon: Earth },
  { name: 'map-pin', pt: 'Localização', icon: MapPin },
  { name: 'compass', pt: 'Explorar / Aventura', icon: Compass },
  { name: 'clock', pt: 'Tempo / Horas', icon: Clock },
  { name: 'calendar-days', pt: 'Agenda / Compromisso', icon: CalendarDays },
  { name: 'info', pt: 'Informação', icon: Info },
  { name: 'triangle-alert', pt: 'Aviso / Atenção', icon: TriangleAlert },
  { name: 'shield-check', pt: 'Seguro / Proteção', icon: ShieldCheck },
  { name: 'shield', pt: 'Proteção', icon: Shield },
  { name: 'fingerprint', pt: 'Biometria / Segurança', icon: Fingerprint },
]

// --- The full remaining Lucide set -------------------------------------------
// Enumerate every icon the library ships (skipping the redundant `*Icon`
// aliases and the base `Icon` component) so the picker offers the entire glyph
// library, not just the curated subset above. Generated icons get a derived
// kebab-case name (the DB identifier) and a humanized label for search, and
// are appended after the curated entries so the hand-tuned ones stay on top.
//
// Bundle note: importing the whole `lucide-react` namespace defeats
// tree-shaking for this module, so the entire icon set ships in the bundle.
// The picker's search box keeps the larger grid navigable. If bundle size ever
// matters, switch rendering to lazy-loaded dynamic imports instead.
const _knownIconNames = new Set(CATEGORY_ICONS.map((e) => e.name))

function _pascalToKebab(name: string): string {
  return name
    .replace(/([a-z0-9])([A-Z])/g, '$1-$2')
    .replace(/([A-Z])([A-Z][a-z])/g, '$1-$2')
    .toLowerCase()
}

function _humanizeIconName(name: string): string {
  return name
    .split('-')
    .map((w) => (w ? w.charAt(0).toUpperCase() + w.slice(1) : w))
    .join(' ')
}

for (const [pascalName, IconComponent] of Object.entries(LucideIcons)) {
  // Keep only the canonical icons: skip the `*Icon` aliases, the base `Icon`
  // component, and the `Lucide*`-prefixed aliases (each icon is also exported
  // as e.g. `LucideHouse`) so we don't list every glyph twice.
  if (
    !/^[A-Z]/.test(pascalName) ||
    pascalName.endsWith('Icon') ||
    pascalName.startsWith('Lucide')
  ) {
    continue
  }
  const name = _pascalToKebab(pascalName)
  if (_knownIconNames.has(name)) continue
  _knownIconNames.add(name)
  CATEGORY_ICONS.push({
    name,
    pt: _humanizeIconName(name),
    icon: IconComponent as LucideIcon,
  })
}

// O(1) lookup map: icon-name → LucideIcon component
export const ICON_MAP: Record<string, LucideIcon> = Object.fromEntries(
  CATEGORY_ICONS.map((entry) => [entry.name, entry.icon])
)

// Icon labels follow the active UI language: tooltips and the picker search
// read the translation. A locale without the key gets the app's fallback
// language through i18next (English); the Portuguese label is the last resort,
// so a missing key never blanks a tooltip or hides an icon from search.
export function getCategoryIconLabel(t: TFunction, name: string): string {
  const key = `categoryIcons.${name}`
  const translated = t(key)
  // i18next echoes the key back when the locale has no entry for it.
  if (typeof translated === 'string' && translated && translated !== key) return translated
  return CATEGORY_ICONS.find((entry) => entry.name === name)?.pt ?? name
}

// Check if a string is an emoji (for backward compatibility with old data)
export function isEmoji(str: string): boolean {
  // Emoji strings are typically 1-2 characters with high code points
  return str.length <= 2 && /\p{Emoji}/u.test(str)
}
