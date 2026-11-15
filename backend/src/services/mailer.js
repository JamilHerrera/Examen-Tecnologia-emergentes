import nodemailer from 'nodemailer';
import { config } from '../config.js';

let transporter;
async function smtpSender(subject, text) {
  transporter ??= nodemailer.createTransport({
    host: config.smtp.host,
    port: config.smtp.port,
    secure: config.smtp.port === 465,
    auth: config.smtp.user ? { user: config.smtp.user, pass: config.smtp.password } : undefined,
  });
  await transporter.sendMail({ from: config.smtp.user || 'alertas@wwi.local', to: config.smtp.to, subject, text });
}

let sender = smtpSender;
let configured = () => Boolean(config.smtp.host && config.smtp.to);

export const emailConfigured = () => configured();
export const sendMail = (subject, text) => sender(subject, text);

/** Permite sustituir el transporte (pruebas de reintentos y fallas de envio). */
export function setMailForTests({ send, enabled }) {
  sender = send ?? smtpSender;
  configured = enabled === undefined ? () => Boolean(config.smtp.host && config.smtp.to) : () => enabled;
}
