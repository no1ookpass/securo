import type { LucideIcon } from 'lucide-react'
// Whole-namespace import powers the "everything else" block at the bottom that
// offers the complete Lucide library (see the bundle note there).
import * as LucideIcons from 'lucide-react'
import {
  House, UtensilsCrossed, Car, ShoppingCart, Pill, Gamepad2,
  Smartphone, BookOpen, ArrowLeftRight, CircleHelp,
  Wallet, CreditCard, Banknote, PiggyBank, TrendingUp, TrendingDown,
  Receipt, ShoppingBag, Gift, Heart, Baby, Dog, Cat,
  Plane, Train, Bus, Fuel, Bike,
  Lightbulb, Droplets, Flame, Wifi, Tv,
  GraduationCap, Briefcase, Building2, Landmark,
  Dumbbell, Shirt, Scissors, Wrench, Hammer,
  Music, Film, Coffee, Beer, Pizza, Salad,
  Stethoscope, Syringe, Cross,
  PartyPopper, TreePine, Umbrella, Globe, Sparkles,
  // Expanded glyph set
  Sandwich, ChefHat, Cake, Cookie, IceCreamCone, Martini, Milk,
  Croissant, Apple, Citrus, Grape, Beef, Drumstick, Egg, Wheat,
  CupSoda, Soup, Popcorn, Candy, Wine, Donut, Hamburger, Dessert, CookingPot,
  ShoppingBasket, Store, Tag, Percent, Package, Box, Gem, Crown, Handbag,
  CarFront, CarTaxiFront, TramFront, TrainFront, Ship, Anchor, Rocket,
  CircleParking, Map,
  HeartPulse, Activity, Bone, Ear, Ambulance, ClipboardPlus,
  PlugZap, Lamp, Fan, Snowflake, ShowerHead, Bath, Ruler,
  Paintbrush, PaintRoller, KeyRound, DoorOpen, Armchair, Sofa, BedDouble,
  Fence, Sprout, Flower2, Recycle,
  Dices, Clapperboard, Drama, Mic2, Piano, Palette, Camera, MonitorPlay,
  Library, Newspaper, Ticket, Balloon, Tent, TentTree, Mountain, Waves,
  Sun, Footprints,
  Coins, HandCoins, CircleDollarSign, BadgeDollarSign,
  ChartLine, ChartPie, ChartColumn, PieChart, LineChart, BarChart3,
  BriefcaseBusiness, ReceiptText, Scale, CirclePercent, CandlestickChart,
  School, BookMarked, PencilLine, Laptop, Monitor, Printer, Factory, Drill,
  HardHat, Truck, PackageCheck,
  Tablet, Watch, Headphones, Radio, Cloud, Database, Server, Cpu,
  BatteryCharging, Repeat, RefreshCw,
  PawPrint, Bird, Fish, Rabbit, Users, HeartHandshake,
  Star, Flag, Medal, Trophy, Award, Earth, MapPin, Compass, Clock,
  CalendarDays, Info, TriangleAlert, ShieldCheck, Shield, Fingerprint
} from 'lucide-react'

export interface CategoryIconEntry {
  name: string      // Lucide icon name (stored in DB)
  label: string     // Portuguese label for search
  icon: LucideIcon  // Component reference
}

export const CATEGORY_ICONS: CategoryIconEntry[] = [
  // Moradia & Casa
  { name: 'house', label: 'Casa / Moradia', icon: House },
  { name: 'lightbulb', label: 'Luz / Energia', icon: Lightbulb },
  { name: 'droplets', label: 'Água', icon: Droplets },
  { name: 'flame', label: 'Gás', icon: Flame },
  { name: 'wifi', label: 'Internet / Wi-Fi', icon: Wifi },
  { name: 'tv', label: 'TV / Streaming', icon: Tv },
  // Alimentação
  { name: 'utensils-crossed', label: 'Alimentação / Restaurante', icon: UtensilsCrossed },
  { name: 'coffee', label: 'Café', icon: Coffee },
  { name: 'beer', label: 'Bebidas / Bar', icon: Beer },
  { name: 'pizza', label: 'Pizza / Fast Food', icon: Pizza },
  { name: 'salad', label: 'Salada / Saudável', icon: Salad },
  // Transporte
  { name: 'car', label: 'Carro / Transporte', icon: Car },
  { name: 'fuel', label: 'Combustível / Gasolina', icon: Fuel },
  { name: 'bus', label: 'Ônibus', icon: Bus },
  { name: 'train', label: 'Trem / Metrô', icon: Train },
  { name: 'plane', label: 'Avião / Viagem', icon: Plane },
  { name: 'bike', label: 'Bicicleta', icon: Bike },
  // Compras
  { name: 'shopping-cart', label: 'Mercado / Supermercado', icon: ShoppingCart },
  { name: 'shopping-bag', label: 'Compras / Loja', icon: ShoppingBag },
  { name: 'gift', label: 'Presente', icon: Gift },
  { name: 'shirt', label: 'Roupa / Vestuário', icon: Shirt },
  // Saúde
  { name: 'pill', label: 'Remédio / Farmácia', icon: Pill },
  { name: 'stethoscope', label: 'Médico / Consulta', icon: Stethoscope },
  { name: 'syringe', label: 'Vacina / Exame', icon: Syringe },
  { name: 'cross', label: 'Hospital / Emergência', icon: Cross },
  { name: 'heart', label: 'Saúde / Bem-estar', icon: Heart },
  { name: 'dumbbell', label: 'Academia / Exercício', icon: Dumbbell },
  // Lazer
  { name: 'gamepad-2', label: 'Jogos / Lazer', icon: Gamepad2 },
  { name: 'music', label: 'Música', icon: Music },
  { name: 'film', label: 'Cinema / Filme', icon: Film },
  { name: 'party-popper', label: 'Festa / Evento', icon: PartyPopper },
  // Tecnologia & Assinaturas
  { name: 'smartphone', label: 'Celular / Telefone', icon: Smartphone },
  { name: 'credit-card', label: 'Cartão de Crédito', icon: CreditCard },
  // Educação
  { name: 'book-open', label: 'Livro / Leitura', icon: BookOpen },
  { name: 'graduation-cap', label: 'Educação / Curso', icon: GraduationCap },
  // Trabalho & Negócios
  { name: 'briefcase', label: 'Trabalho / Negócios', icon: Briefcase },
  { name: 'building-2', label: 'Empresa / Escritório', icon: Building2 },
  { name: 'landmark', label: 'Banco / Governo', icon: Landmark },
  // Finanças
  { name: 'wallet', label: 'Carteira', icon: Wallet },
  { name: 'banknote', label: 'Dinheiro', icon: Banknote },
  { name: 'piggy-bank', label: 'Poupança / Investimento', icon: PiggyBank },
  { name: 'trending-up', label: 'Rendimento / Lucro', icon: TrendingUp },
  { name: 'trending-down', label: 'Prejuízo / Perda', icon: TrendingDown },
  { name: 'receipt', label: 'Recibo / Nota Fiscal', icon: Receipt },
  { name: 'arrow-left-right', label: 'Transferência', icon: ArrowLeftRight },
  // Família & Pets
  { name: 'baby', label: 'Bebê / Criança', icon: Baby },
  { name: 'dog', label: 'Pet / Cachorro', icon: Dog },
  { name: 'cat', label: 'Pet / Gato', icon: Cat },
  // Serviços & Manutenção
  { name: 'scissors', label: 'Cabelo / Beleza', icon: Scissors },
  { name: 'wrench', label: 'Manutenção / Reparo', icon: Wrench },
  { name: 'hammer', label: 'Construção / Reforma', icon: Hammer },
  // Outros
  { name: 'tree-pine', label: 'Natureza / Jardim', icon: TreePine },
  { name: 'umbrella', label: 'Seguro', icon: Umbrella },
  { name: 'globe', label: 'Internacional', icon: Globe },
  { name: 'sparkles', label: 'Especial', icon: Sparkles },
  { name: 'circle-help', label: 'Outros / Indefinido', icon: CircleHelp },
  // Comida & Delivery
  { name: 'sandwich', label: 'Sanduíche / Lanche', icon: Sandwich },
  { name: 'chef-hat', label: 'Chef / Delivery', icon: ChefHat },
  { name: 'cake', label: 'Bolo / Sobremesa', icon: Cake },
  { name: 'cookie', label: 'Biscoito / Lanche', icon: Cookie },
  { name: 'ice-cream-cone', label: 'Sorvete', icon: IceCreamCone },
  { name: 'martini', label: 'Drinks / Coquetel', icon: Martini },
  { name: 'milk', label: 'Leite / Mercado', icon: Milk },
  { name: 'croissant', label: 'Padaria', icon: Croissant },
  { name: 'apple', label: 'Frutas', icon: Apple },
  { name: 'citrus', label: 'Frutas Cítricas', icon: Citrus },
  { name: 'grape', label: 'Uvas / Vinho', icon: Grape },
  { name: 'beef', label: 'Açougue / Carne', icon: Beef },
  { name: 'drumstick', label: 'Frango', icon: Drumstick },
  { name: 'egg', label: 'Ovos / Café da Manhã', icon: Egg },
  { name: 'wheat', label: 'Padaria / Farinha', icon: Wheat },
  { name: 'cup-soda', label: 'Refrigerante', icon: CupSoda },
  { name: 'soup', label: 'Sopa / Caldo', icon: Soup },
  { name: 'popcorn', label: 'Cinema / Pipoca', icon: Popcorn },
  { name: 'candy', label: 'Doces', icon: Candy },
  { name: 'wine', label: 'Vinho / Bebida', icon: Wine },
  { name: 'donut', label: 'Donut / Café', icon: Donut },
  { name: 'hamburger', label: 'Lanchonete / Fast Food', icon: Hamburger },
  { name: 'dessert', label: 'Sobremesa', icon: Dessert },
  { name: 'cooking-pot', label: 'Culinária / Cozinha', icon: CookingPot },
  // Compras & Varejo
  { name: 'shopping-basket', label: 'Cestinha / Feira', icon: ShoppingBasket },
  { name: 'store', label: 'Loja / Varejo', icon: Store },
  { name: 'tag', label: 'Etiqueta / Promoção', icon: Tag },
  { name: 'percent', label: 'Desconto / %', icon: Percent },
  { name: 'package', label: 'Pacote / Encomenda', icon: Package },
  { name: 'box', label: 'Caixa', icon: Box },
  { name: 'gem', label: 'Joia / Luxo', icon: Gem },
  { name: 'crown', label: 'Premium / Assinatura', icon: Crown },
  { name: 'handbag', label: 'Bolsa / Acessório', icon: Handbag },
  // Transporte
  { name: 'car-front', label: 'Carro (Frente)', icon: CarFront },
  { name: 'car-taxi-front', label: 'Táxi / Uber', icon: CarTaxiFront },
  { name: 'tram-front', label: 'Bonde / Ônibus', icon: TramFront },
  { name: 'train-front', label: 'Trem / Metrô', icon: TrainFront },
  { name: 'ship', label: 'Navio / Cruzeiro', icon: Ship },
  { name: 'anchor', label: 'Porto / Náutico', icon: Anchor },
  { name: 'rocket', label: 'Startup / Alto Risco', icon: Rocket },
  { name: 'circle-parking', label: 'Estacionamento', icon: CircleParking },
  { name: 'map', label: 'Mapa / Rota', icon: Map },
  // Saúde
  { name: 'heart-pulse', label: 'Pulso / Cardiologia', icon: HeartPulse },
  { name: 'activity', label: 'Atividade / Saúde', icon: Activity },
  { name: 'bone', label: 'Ortopedia', icon: Bone },
  { name: 'ear', label: 'Ouvido / Fono', icon: Ear },
  { name: 'ambulance', label: 'Ambulância / Emergência', icon: Ambulance },
  { name: 'clipboard-plus', label: 'Consulta / Exame', icon: ClipboardPlus },
  // Casa & Serviços
  { name: 'plug-zap', label: 'Energia / Recarga', icon: PlugZap },
  { name: 'lamp', label: 'Lâmpada / Iluminação', icon: Lamp },
  { name: 'fan', label: 'Ventilador / Ar', icon: Fan },
  { name: 'snowflake', label: 'Ar-Condicionado', icon: Snowflake },
  { name: 'shower-head', label: 'Água / Banho', icon: ShowerHead },
  { name: 'bath', label: 'Banheiro', icon: Bath },
  { name: 'ruler', label: 'Medidas / Reforma', icon: Ruler },
  { name: 'paintbrush', label: 'Pintura', icon: Paintbrush },
  { name: 'paint-roller', label: 'Reforma / Pintura', icon: PaintRoller },
  { name: 'key-round', label: 'Chave / Aluguel', icon: KeyRound },
  { name: 'door-open', label: 'Porta / Entrada', icon: DoorOpen },
  { name: 'armchair', label: 'Sofá / Móveis', icon: Armchair },
  { name: 'sofa', label: 'Sofá / Móveis', icon: Sofa },
  { name: 'bed-double', label: 'Cama / Móveis', icon: BedDouble },
  { name: 'fence', label: 'Cerca / Jardim', icon: Fence },
  { name: 'sprout', label: 'Plantas / Jardim', icon: Sprout },
  { name: 'flower-2', label: 'Flores / Jardinagem', icon: Flower2 },
  { name: 'recycle', label: 'Reciclagem / Lixo', icon: Recycle },
  // Lazer & Entretenimento
  { name: 'dices', label: 'Jogos de Mesa', icon: Dices },
  { name: 'clapperboard', label: 'Produção / Filme', icon: Clapperboard },
  { name: 'drama', label: 'Teatro / Cultura', icon: Drama },
  { name: 'mic-2', label: 'Karaokê / Música', icon: Mic2 },
  { name: 'piano', label: 'Piano / Música', icon: Piano },
  { name: 'palette', label: 'Arte / Criatividade', icon: Palette },
  { name: 'camera', label: 'Câmera / Foto', icon: Camera },
  { name: 'monitor-play', label: 'Streaming / Vídeo', icon: MonitorPlay },
  { name: 'library', label: 'Biblioteca', icon: Library },
  { name: 'newspaper', label: 'Jornal / Notícias', icon: Newspaper },
  { name: 'ticket', label: 'Ingresso / Evento', icon: Ticket },
  { name: 'balloon', label: 'Festa / Decoração', icon: Balloon },
  { name: 'tent', label: 'Acampamento', icon: Tent },
  { name: 'tent-tree', label: 'Camping / Natureza', icon: TentTree },
  { name: 'mountain', label: 'Trilha / Aventura', icon: Mountain },
  { name: 'waves', label: 'Praia / Surfe', icon: Waves },
  { name: 'sun', label: 'Verão / Sol', icon: Sun },
  { name: 'footprints', label: 'Caminhada / Pet', icon: Footprints },
  // Finanças
  { name: 'coins', label: 'Moedas / Troco', icon: Coins },
  { name: 'hand-coins', label: 'Doação / Pagamento', icon: HandCoins },
  { name: 'circle-dollar-sign', label: 'Dólar', icon: CircleDollarSign },
  { name: 'badge-dollar-sign', label: 'Renda / US$', icon: BadgeDollarSign },
  { name: 'chart-line', label: 'Gráfico / Análise', icon: ChartLine },
  { name: 'chart-pie', label: 'Gráfico de Pizza', icon: ChartPie },
  { name: 'chart-column', label: 'Gráfico de Barras', icon: ChartColumn },
  { name: 'pie-chart', label: 'Gráfico de Pizza', icon: PieChart },
  { name: 'line-chart', label: 'Gráfico de Linha', icon: LineChart },
  { name: 'bar-chart-3', label: 'Gráfico de Barras', icon: BarChart3 },
  { name: 'briefcase-business', label: 'Negócios / PJ', icon: BriefcaseBusiness },
  { name: 'receipt-text', label: 'Nota / Recibo', icon: ReceiptText },
  { name: 'scale', label: 'Impostos / Justiça', icon: Scale },
  { name: 'circle-percent', label: 'Porcentagem', icon: CirclePercent },
  { name: 'candlestick-chart', label: 'Ações / Investimento', icon: CandlestickChart },
  // Trabalho & Educação
  { name: 'school', label: 'Escola / Educação', icon: School },
  { name: 'book-marked', label: 'Apostila / Estudo', icon: BookMarked },
  { name: 'pencil-line', label: 'Edição / Anotações', icon: PencilLine },
  { name: 'laptop', label: 'Notebook / Trabalho', icon: Laptop },
  { name: 'monitor', label: 'Monitor / Escritório', icon: Monitor },
  { name: 'printer', label: 'Impressora', icon: Printer },
  { name: 'factory', label: 'Fábrica / Indústria', icon: Factory },
  { name: 'drill', label: 'Ferramenta / Furadeira', icon: Drill },
  { name: 'hard-hat', label: 'Obra / Construção', icon: HardHat },
  { name: 'truck', label: 'Caminhão / Frete', icon: Truck },
  { name: 'package-check', label: 'Encomenda / Entrega', icon: PackageCheck },
  // Tecnologia & Assinaturas
  { name: 'tablet', label: 'Tablet', icon: Tablet },
  { name: 'watch', label: 'Relógio', icon: Watch },
  { name: 'headphones', label: 'Fone / Áudio', icon: Headphones },
  { name: 'radio', label: 'Rádio', icon: Radio },
  { name: 'cloud', label: 'Nuvem / Armazenamento', icon: Cloud },
  { name: 'database', label: 'Dados / Servidor', icon: Database },
  { name: 'server', label: 'Servidor / Hosting', icon: Server },
  { name: 'cpu', label: 'Hardware / TI', icon: Cpu },
  { name: 'battery-charging', label: 'Recarga / Energia', icon: BatteryCharging },
  { name: 'repeat', label: 'Assinatura / Recorrente', icon: Repeat },
  { name: 'refresh-cw', label: 'Atualização / Renovação', icon: RefreshCw },
  // Pets & Família
  { name: 'paw-print', label: 'Pet / Pata', icon: PawPrint },
  { name: 'bird', label: 'Pet / Pássaro', icon: Bird },
  { name: 'fish', label: 'Pet / Peixe', icon: Fish },
  { name: 'rabbit', label: 'Pet / Coelho', icon: Rabbit },
  { name: 'users', label: 'Família / Grupo', icon: Users },
  { name: 'heart-handshake', label: 'Doação / Solidariedade', icon: HeartHandshake },
  // Outros
  { name: 'star', label: 'Favorito / Destaque', icon: Star },
  { name: 'flag', label: 'Bandeira / País', icon: Flag },
  { name: 'medal', label: 'Prêmio / Reconhecimento', icon: Medal },
  { name: 'trophy', label: 'Troféu / Conquista', icon: Trophy },
  { name: 'award', label: 'Premiação', icon: Award },
  { name: 'earth', label: 'Mundo / Global', icon: Earth },
  { name: 'map-pin', label: 'Localização', icon: MapPin },
  { name: 'compass', label: 'Explorar / Aventura', icon: Compass },
  { name: 'clock', label: 'Tempo / Horas', icon: Clock },
  { name: 'calendar-days', label: 'Agenda / Compromisso', icon: CalendarDays },
  { name: 'info', label: 'Informação', icon: Info },
  { name: 'triangle-alert', label: 'Aviso / Atenção', icon: TriangleAlert },
  { name: 'shield-check', label: 'Seguro / Proteção', icon: ShieldCheck },
  { name: 'shield', label: 'Proteção', icon: Shield },
  { name: 'fingerprint', label: 'Biometria / Segurança', icon: Fingerprint },
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
    label: _humanizeIconName(name),
    icon: IconComponent as LucideIcon,
  })
}

// O(1) lookup map: icon-name → LucideIcon component
export const ICON_MAP: Record<string, LucideIcon> = Object.fromEntries(
  CATEGORY_ICONS.map((entry) => [entry.name, entry.icon])
)

// Check if a string is an emoji (for backward compatibility with old data)
export function isEmoji(str: string): boolean {
  // Emoji strings are typically 1-2 characters with high code points
  return str.length <= 2 && /\p{Emoji}/u.test(str)
}
